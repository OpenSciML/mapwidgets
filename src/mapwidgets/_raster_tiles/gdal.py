"""GDAL-backed GeoTIFF tile generation."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .common import (
    DEFAULT_TILE_SIZE,
    fill_missing_tiles,
    prepare_output_dir,
    resolve_tile_plan,
    tile_directory_satisfies,
    worker_count,
    write_tile_metadata,
)


def generate_geotiff_tiles_gdal(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    min_zoom: int | None = None,
    max_zoom: int | None = None,
    zoom_levels: Iterable[int] | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    overwrite: bool = False,
    max_tiles: int = 20_000,
    processes: int | None = None,
    resampling: str = "bilinear",
    name: str | None = None,
    opacity: float = 1.0,
) -> Path:
    """Generate XYZ PNG tiles with ``osgeo_utils.gdal2tiles``.

    Args:
        input_path: Source GeoTIFF path.
        output_dir: Directory where `{z}/{x}/{y}.png` tiles are written.
        min_zoom: Minimum generated zoom when `zoom_levels` is omitted.
        max_zoom: Maximum generated zoom when `zoom_levels` is omitted.
        zoom_levels: Explicit zoom levels to generate.
        tile_size: Pixel width and height for generated square tiles.
        overwrite: Whether to replace an existing tile folder.
        max_tiles: Safety limit for generated tile count.
        processes: GDAL worker process count.
        resampling: GDAL resampling method passed to gdal2tiles.
        name: Layer name written to metadata.
        opacity: Raster opacity written to metadata.

    Returns:
        Tile output directory.

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        RuntimeError: If GDAL's `gdal2tiles` module is unavailable or fails.
        ValueError: If the raster cannot produce a valid tile plan.
    """
    source = Path(input_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"GeoTIFF does not exist: {source}")

    output = Path(output_dir).expanduser() if output_dir else source.with_suffix("")
    levels, bounds, _ = resolve_tile_plan(
        source,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        zoom_levels=zoom_levels,
        tile_size=tile_size,
        max_tiles=max_tiles,
    )

    if not overwrite and tile_directory_satisfies(
        output,
        bounds=bounds,
        min_zoom=min(levels),
        max_zoom=max(levels),
        tile_size=tile_size,
    ):
        return output

    prepare_output_dir(output, overwrite=overwrite)
    zoom_arg = f"{min(levels)}-{max(levels)}" if len(levels) > 1 else str(levels[0])
    argv = [
        "--xyz",
        "--webviewer=none",
        f"--processes={worker_count(processes)}",
        f"--tilesize={tile_size}",
        "-r",
        resampling,
        "-z",
        zoom_arg,
        str(source),
        str(output),
    ]

    try:
        from osgeo_utils import gdal2tiles
    except Exception as exc:
        raise RuntimeError(
            "GDAL tiling requires osgeo_utils.gdal2tiles. Install GDAL with "
            "`pip install mapwidgets[geospatial]` or use backend='python'."
        ) from exc

    result = gdal2tiles.main(argv, called_from_main=False)
    if result not in (0, None):
        raise RuntimeError(f"gdal2tiles failed with exit code {result}.")

    fill_missing_tiles(
        output,
        bounds=bounds,
        min_zoom=min(levels),
        max_zoom=max(levels),
        tile_size=tile_size,
    )
    write_tile_metadata(
        output,
        bounds=bounds,
        min_zoom=min(levels),
        max_zoom=max(levels),
        tile_size=tile_size,
        name=name or source.stem,
        opacity=opacity,
    )
    return output
