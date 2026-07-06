"""Shared raster tile planning and metadata utilities."""

from __future__ import annotations

import json
import math
import shutil
import time
import zlib
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from mapwidgets.layers._utils import read_geotiff_bounds

WEB_MERCATOR_CRS = "EPSG:3857"
WGS84_CRS = "EPSG:4326"
WEB_MERCATOR_HALF_WORLD = 20037508.342789244
WEB_MERCATOR_WORLD_WIDTH = WEB_MERCATOR_HALF_WORLD * 2
DEFAULT_TILE_SIZE = 256
TileBackend = Literal["gdal", "python"]
TransparentMatch = Literal["any", "all"]


def optimize_geotiff_for_tiling(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    overwrite: bool = False,
    block_size: int = 512,
    compress: str = "DEFLATE",
    resampling: str = "AVERAGE",
    num_threads: str = "ALL_CPUS",
) -> Path:
    """Create a tiled COG-style GeoTIFF optimized for web tile generation.

    Args:
        input_path: Source GeoTIFF path.
        output_path: Destination path for the optimized GeoTIFF. When omitted,
            a sibling ``*_optimized.tif`` file is created.
        overwrite: Whether to replace an existing optimized file.
        block_size: Internal COG block size in pixels.
        compress: GDAL COG compression method.
        resampling: Overview resampling method.
        num_threads: GDAL thread setting used during conversion.

    Returns:
        Path to the optimized GeoTIFF.

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        RuntimeError: If GDAL is unavailable or fails to create the output.
    """
    source = Path(input_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"GeoTIFF does not exist: {source}")

    output = (
        Path(output_path).expanduser()
        if output_path is not None
        else source.with_name(f"{source.stem}_optimized.tif")
    )
    if output.exists() and not overwrite:
        return output
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from osgeo import gdal
    except Exception as exc:
        raise RuntimeError(
            "GDAL Python bindings are required to optimize GeoTIFFs. "
            "Install/sync GDAL or use an already optimized COG."
        ) from exc

    options = gdal.TranslateOptions(
        format="COG",
        creationOptions=[
            f"BLOCKSIZE={block_size}",
            f"COMPRESS={compress}",
            f"RESAMPLING={resampling}",
            "OVERVIEWS=AUTO",
            "BIGTIFF=IF_SAFER",
            f"NUM_THREADS={num_threads}",
        ],
    )
    result = gdal.Translate(str(output), str(source), options=options)
    if result is None:
        raise RuntimeError(f"GDAL failed to optimize GeoTIFF: {source}")
    result = None
    return output


def prepare_output_dir(output: Path, *, overwrite: bool) -> None:
    """Create or replace a tile output directory."""
    if overwrite and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)


def resolve_tile_plan(
    path: Path,
    *,
    min_zoom: int | None,
    max_zoom: int | None,
    zoom_levels: Iterable[int] | None,
    tile_size: int,
    max_tiles: int,
) -> tuple[list[int], dict[str, float], tuple[float, float, float, float]]:
    """Resolve zoom levels, WGS84 bounds, and Web Mercator bounds."""
    try:
        import rasterio
    except ImportError as exc:
        raise ImportError(
            "Raster tiling requires the geospatial extra. Install with "
            "`pip install mapwidgets[geospatial]`."
        ) from exc

    with rasterio.open(path) as source:
        if source.crs is None:
            raise ValueError("GeoTIFF must have a CRS before generating map tiles.")

        bounds_3857 = transform_bounds(
            source.crs,
            WEB_MERCATOR_CRS,
            *source.bounds,
            densify_pts=21,
        )
        levels = resolve_zoom_levels(
            source,
            bounds_3857,
            zoom_levels=zoom_levels,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            tile_size=tile_size,
        )

    tile_count = sum(tile_count_for_bounds(bounds_3857, zoom) for zoom in levels)
    if tile_count > max_tiles:
        raise ValueError(
            f"Refusing to generate {tile_count} tiles. Pass narrower zoom levels "
            "or increase max_tiles explicitly."
        )

    bounds = read_geotiff_bounds(path)
    if bounds is None:
        raise ValueError("Could not read GeoTIFF bounds.")
    return levels, bounds, bounds_3857


def resolve_zoom_levels(
    source: object,
    bounds_3857: tuple[float, float, float, float],
    *,
    zoom_levels: Iterable[int] | None,
    min_zoom: int | None,
    max_zoom: int | None,
    tile_size: int,
) -> list[int]:
    """Resolve explicit or estimated tile zoom levels."""
    if zoom_levels is not None:
        levels = sorted({int(zoom) for zoom in zoom_levels})
    else:
        estimated_max_zoom = estimate_native_zoom(source, bounds_3857, tile_size)
        max_zoom = estimated_max_zoom if max_zoom is None else int(max_zoom)
        min_zoom = max(0, max_zoom - 2) if min_zoom is None else int(min_zoom)
        levels = list(range(min_zoom, max_zoom + 1))

    if not levels:
        raise ValueError("At least one zoom level is required.")
    if levels[0] < 0 or levels[-1] > 30:
        raise ValueError("Zoom levels must be between 0 and 30.")
    return levels


def estimate_native_zoom(
    source: object,
    bounds_3857: tuple[float, float, float, float],
    tile_size: int,
) -> int:
    """Estimate the closest web-map zoom for the raster resolution."""
    west, south, east, north = bounds_3857
    width = max(getattr(source, "width", 1), 1)
    height = max(getattr(source, "height", 1), 1)
    x_resolution = abs(east - west) / width
    y_resolution = abs(north - south) / height
    resolution = max(x_resolution, y_resolution)
    if resolution <= 0 or not math.isfinite(resolution):
        return 18
    zoom = math.log2(WEB_MERCATOR_WORLD_WIDTH / (tile_size * resolution))
    return max(0, min(22, int(round(zoom))))


def tile_count_for_bounds(
    bounds_3857: tuple[float, float, float, float],
    zoom: int,
) -> int:
    """Return the number of XYZ tiles intersecting bounds at one zoom level."""
    west, south, east, north = bounds_3857
    x_min = mercator_x_to_tile(west, zoom)
    x_max = mercator_x_to_tile(east, zoom)
    y_min = mercator_y_to_tile(north, zoom)
    y_max = mercator_y_to_tile(south, zoom)
    return (x_max - x_min + 1) * (y_max - y_min + 1)


def tile_ranges_for_bounds(
    bounds_3857: tuple[float, float, float, float],
    zoom: int,
) -> tuple[int, int, int, int]:
    """Return inclusive XYZ x/y tile ranges for Web Mercator bounds."""
    west, south, east, north = bounds_3857
    return (
        mercator_x_to_tile(west, zoom),
        mercator_x_to_tile(east, zoom),
        mercator_y_to_tile(north, zoom),
        mercator_y_to_tile(south, zoom),
    )


def tile_bounds_3857(
    x: int,
    y: int,
    zoom: int,
) -> tuple[float, float, float, float]:
    """Return Web Mercator bounds for one XYZ tile."""
    tiles = 2**zoom
    tile_width = WEB_MERCATOR_WORLD_WIDTH / tiles
    west = -WEB_MERCATOR_HALF_WORLD + x * tile_width
    east = west + tile_width
    north = WEB_MERCATOR_HALF_WORLD - y * tile_width
    south = north - tile_width
    return west, south, east, north


def mercator_x_to_tile(x: float, zoom: int) -> int:
    """Convert Web Mercator x coordinate to XYZ tile x index."""
    tiles = 2**zoom
    value = (x + WEB_MERCATOR_HALF_WORLD) / WEB_MERCATOR_WORLD_WIDTH * tiles
    return clamp_tile_index(value, zoom)


def mercator_y_to_tile(y: float, zoom: int) -> int:
    """Convert Web Mercator y coordinate to XYZ tile y index."""
    tiles = 2**zoom
    value = (WEB_MERCATOR_HALF_WORLD - y) / WEB_MERCATOR_WORLD_WIDTH * tiles
    return clamp_tile_index(value, zoom)


def clamp_tile_index(value: float, zoom: int) -> int:
    """Clamp a floating tile coordinate to a valid integer tile index."""
    max_index = 2**zoom - 1
    return max(0, min(max_index, int(value)))


def worker_count(processes: int | None) -> int:
    """Resolve a conservative worker count."""
    if processes is not None:
        return max(1, int(processes))
    return 1


def write_tile_metadata(
    output_dir: Path,
    *,
    bounds: dict[str, float],
    min_zoom: int,
    max_zoom: int,
    tile_size: int,
    name: str,
    opacity: float,
) -> None:
    """Write layer metadata next to generated tiles."""
    metadata = {
        "type": "raster",
        "id": output_dir.name,
        "name": name,
        "baseUrl": output_dir.resolve().as_uri(),
        "bounds": bounds,
        "minZoom": min_zoom,
        "maxZoom": max_zoom,
        "tileSize": tile_size,
        "opacity": opacity,
        "cacheKey": str(int(time.time() * 1000)),
    }
    with (output_dir / "metadata.json").open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2)


def transform_bounds(
    *args: object, **kwargs: object
) -> tuple[float, float, float, float]:
    """Import rasterio lazily and transform bounds."""
    try:
        from rasterio.warp import transform_bounds as rasterio_transform_bounds
    except ImportError as exc:
        raise ImportError(
            "Raster tiling requires the geospatial extra. Install with "
            "`pip install mapwidgets[geospatial]`."
        ) from exc

    return rasterio_transform_bounds(*args, **kwargs)


def validate_tile_directory(
    tiles_dir: str | Path,
    *,
    bounds: dict[str, float],
    min_zoom: int,
    max_zoom: int,
    tile_size: int = DEFAULT_TILE_SIZE,
) -> None:
    """Validate expected XYZ tile files exist for bounds and zoom range."""
    directory = Path(tiles_dir).expanduser()
    if not directory.exists():
        raise FileNotFoundError(f"Tile directory does not exist: {directory}")

    missing: list[Path] = []
    for path in expected_tile_paths(
        directory,
        bounds=bounds,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
    ):
        if not path.exists() or png_size(path) != (tile_size, tile_size):
            missing.append(path)
            if len(missing) >= 5:
                break

    if missing:
        examples = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Tile directory is incomplete. Missing: {examples}")


def fill_missing_tiles(
    tiles_dir: str | Path,
    *,
    bounds: dict[str, float],
    min_zoom: int,
    max_zoom: int,
    tile_size: int = DEFAULT_TILE_SIZE,
) -> int:
    """Write transparent PNGs for missing XYZ tiles inside layer bounds."""
    directory = Path(tiles_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)

    filled = 0
    for path in expected_tile_paths(
        directory,
        bounds=bounds,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
    ):
        if path.exists() and png_size(path) == (tile_size, tile_size):
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(transparent_png(tile_size))
        filled += 1
    return filled


def tile_directory_satisfies(
    tiles_dir: Path,
    *,
    bounds: dict[str, float],
    min_zoom: int,
    max_zoom: int,
    tile_size: int,
) -> bool:
    """Return whether a tile directory already covers the requested range."""
    metadata_path = tiles_dir / "metadata.json"
    if not metadata_path.exists():
        return False
    try:
        metadata = json.loads(metadata_path.read_text())
        if metadata.get("minZoom", 99) > min_zoom:
            return False
        if metadata.get("maxZoom", -1) < max_zoom:
            return False
        if metadata.get("tileSize", tile_size) != tile_size:
            return False
        filled = fill_missing_tiles(
            tiles_dir,
            bounds=bounds,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            tile_size=tile_size,
        )
        if filled:
            write_tile_metadata(
                tiles_dir,
                bounds=bounds,
                min_zoom=min_zoom,
                max_zoom=max_zoom,
                tile_size=tile_size,
                name=metadata.get("name", tiles_dir.name),
                opacity=metadata.get("opacity", 1.0),
            )
        validate_tile_directory(
            tiles_dir,
            bounds=bounds,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
        )
    except Exception:
        return False
    return True


def transparent_png(size: int) -> bytes:
    """Return a transparent RGBA PNG with the requested square size."""
    rgba = b"\x00\x00\x00\x00" * size * size
    return rgba_png(rgba, size, size)


def rgba_png(rgba: bytes, width: int, height: int) -> bytes:
    """Return PNG bytes for tightly packed RGBA pixels.

    Args:
        rgba: Tightly packed RGBA bytes in row-major order.
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Encoded PNG bytes.
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        """Encode one PNG chunk.

        Args:
            kind: Four-byte PNG chunk type.
            data: Chunk payload.

        Returns:
            Length-prefixed PNG chunk bytes with CRC.
        """
        crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        return len(data).to_bytes(4, "big") + kind + data + crc.to_bytes(4, "big")

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = (
        width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"
    )
    stride = width * 4
    raw = b"".join(
        b"\x00" + rgba[row : row + stride] for row in range(0, len(rgba), stride)
    )
    return (
        signature
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def png_size(path: Path) -> tuple[int, int] | None:
    """Return PNG image dimensions from the header."""
    try:
        with path.open("rb") as file:
            header = file.read(24)
    except OSError:
        return None
    if not header.startswith(b"\x89PNG\r\n\x1a\n") or header[12:16] != b"IHDR":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def expected_tile_paths(
    tiles_dir: Path,
    *,
    bounds: dict[str, float],
    min_zoom: int,
    max_zoom: int,
) -> Iterable[Path]:
    """Yield expected XYZ tile paths for bounds and zoom range."""
    bounds_3857 = transform_bounds(
        WGS84_CRS,
        WEB_MERCATOR_CRS,
        bounds["west"],
        bounds["south"],
        bounds["east"],
        bounds["north"],
        densify_pts=21,
    )
    for zoom in range(min_zoom, max_zoom + 1):
        x_min, x_max, y_min, y_max = tile_ranges_for_bounds(bounds_3857, zoom)
        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                yield tiles_dir / str(zoom) / str(x) / f"{y}.png"
