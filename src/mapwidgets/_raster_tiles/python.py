"""Rasterio-backed GeoTIFF tile generation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Literal

import numpy as np

from .common import (
    DEFAULT_TILE_SIZE,
    WEB_MERCATOR_CRS,
    TransparentMatch,
    prepare_output_dir,
    resolve_tile_plan,
    rgba_png,
    tile_bounds_3857,
    tile_directory_satisfies,
    tile_ranges_for_bounds,
    write_tile_metadata,
)

StretchMethod = Literal["percentiles", "linear"]


def generate_geotiff_tiles_python(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    bands: Sequence[int] = (1, 2, 3),
    min_zoom: int | None = None,
    max_zoom: int | None = None,
    zoom_levels: Iterable[int] | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    overwrite: bool = False,
    max_tiles: int = 20_000,
    resampling: str = "bilinear",
    name: str | None = None,
    opacity: float = 1.0,
    stretch_method: StretchMethod = "percentiles",
    transparent_values: Sequence[float] | None = (0,),
    transparent_ranges: Sequence[tuple[float | None, float | None]] | None = None,
    transparent_match: TransparentMatch = "any",
    colormap: str | None = None,
    value_range: tuple[float, float] | None = None,
    stretch_sample_size: int = 1024,
) -> Path:
    """Generate XYZ PNG tiles from a GeoTIFF with rasterio.

    Args:
        input_path: Source GeoTIFF path.
        output_dir: Directory where `{z}/{x}/{y}.png` tiles are written.
        bands: One-based source bands to render. One band renders grayscale or
            a colormap; two bands duplicate the second channel; three or more
            use the first three selected bands as RGB.
        min_zoom: Minimum generated zoom when `zoom_levels` is omitted.
        max_zoom: Maximum generated zoom when `zoom_levels` is omitted.
        zoom_levels: Explicit zoom levels to generate.
        tile_size: Pixel width and height for generated square tiles.
        overwrite: Whether to replace an existing tile folder.
        max_tiles: Safety limit for generated tile count.
        resampling: Rasterio resampling enum name.
        name: Layer name written to metadata.
        opacity: Raster opacity written to metadata.
        stretch_method: Display scaling method for non-colormapped output.
        transparent_values: Exact source values hidden in output alpha.
        transparent_ranges: Inclusive source value ranges hidden in output alpha.
        transparent_match: Whether transparency applies when any or all
            selected bands match.
        colormap: Optional Matplotlib colormap for single-band rendering.
        value_range: Optional `(min, max)` normalization range.
        stretch_sample_size: Maximum sampled width or height used to estimate
            global display ranges.

    Returns:
        Tile output directory.

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        ImportError: If rasterio or an optional colormap dependency is missing.
        ValueError: If band indexes, stretch settings, or tile planning inputs
            are invalid.
    """
    try:
        import rasterio
    except ImportError as exc:
        raise ImportError(
            "Python tiling requires the geospatial extra. Install with "
            "`pip install mapwidgets[geospatial]`."
        ) from exc

    source = Path(input_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"GeoTIFF does not exist: {source}")

    output = Path(output_dir).expanduser() if output_dir else source.with_suffix("")
    levels, bounds, bounds_3857 = resolve_tile_plan(
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

    selected_bands = tuple(int(band) for band in bands)
    prepare_output_dir(output, overwrite=overwrite)
    with rasterio.open(source) as dataset:
        _validate_bands(selected_bands, dataset.count)
        stretch_ranges = _compute_stretch_ranges(
            dataset,
            selected_bands,
            stretch_method=stretch_method,
            value_range=value_range,
            sample_size=stretch_sample_size,
        )
        for zoom in levels:
            x_min, x_max, y_min, y_max = tile_ranges_for_bounds(bounds_3857, zoom)
            for x in range(x_min, x_max + 1):
                for y in range(y_min, y_max + 1):
                    tile = _read_tile(
                        dataset,
                        selected_bands,
                        x=x,
                        y=y,
                        zoom=zoom,
                        tile_size=tile_size,
                        resampling=resampling,
                    )
                    rgba = _render_tile(
                        tile,
                        stretch_ranges=stretch_ranges,
                        transparent_values=transparent_values,
                        transparent_ranges=transparent_ranges,
                        transparent_match=transparent_match,
                        colormap=colormap,
                    )
                    path = output / str(zoom) / str(x) / f"{y}.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(rgba_png(rgba.tobytes(), tile_size, tile_size))

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


def _validate_bands(bands: tuple[int, ...], band_count: int) -> None:
    """Validate one-based band indexes.

    Args:
        bands: One-based band indexes requested for rendering.
        band_count: Number of bands available in the source raster.

    Raises:
        ValueError: If no bands are provided or any band is out of bounds.
    """
    if not bands:
        raise ValueError("At least one band is required.")
    invalid = [band for band in bands if band < 1 or band > band_count]
    if invalid:
        raise ValueError(
            f"Invalid band indexes {invalid}; source has {band_count} band(s)."
        )


def _compute_stretch_ranges(
    dataset: Any,
    bands: tuple[int, ...],
    *,
    stretch_method: StretchMethod,
    value_range: tuple[float, float] | None,
    sample_size: int,
) -> tuple[tuple[float, float], ...]:
    """Compute display stretch ranges for selected source bands.

    Args:
        dataset: Open rasterio dataset.
        bands: One-based source bands selected for rendering.
        stretch_method: Display scaling method.
        value_range: Explicit `(min, max)` range that overrides sampling.
        sample_size: Maximum sampled width or height.

    Returns:
        One `(min, max)` stretch range per rendered band.

    Raises:
        ValueError: If `stretch_method` is unsupported.
    """
    indexes = list(bands[:3])
    if value_range is not None:
        return tuple(value_range for _ in indexes)

    height = max(1, int(dataset.height))
    width = max(1, int(dataset.width))
    scale = max(height / sample_size, width / sample_size, 1)
    out_shape = (len(indexes), max(1, int(height / scale)), max(1, int(width / scale)))
    sample = dataset.read(indexes, masked=True, out_shape=out_shape)

    ranges: list[tuple[float, float]] = []
    for band in sample:
        values = np.asarray(band.compressed() if np.ma.isMaskedArray(band) else band)
        values = values[np.isfinite(values)]
        if values.size == 0:
            ranges.append((0.0, 1.0))
            continue
        if stretch_method == "percentiles":
            low, high = np.nanpercentile(values, [2, 98])
        elif stretch_method == "linear":
            low, high = np.nanmin(values), np.nanmax(values)
        else:
            raise ValueError("stretch_method must be 'percentiles' or 'linear'.")
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            high = low + 1.0
        ranges.append((float(low), float(high)))
    return tuple(ranges)


def _read_tile(
    dataset: Any,
    bands: tuple[int, ...],
    *,
    x: int,
    y: int,
    zoom: int,
    tile_size: int,
    resampling: str,
) -> np.ndarray:
    """Read and reproject one XYZ tile into selected band arrays.

    Args:
        dataset: Open rasterio dataset.
        bands: One-based source bands selected for rendering.
        x: XYZ tile x index.
        y: XYZ tile y index.
        zoom: Web-map zoom level.
        tile_size: Pixel width and height of the destination tile.
        resampling: Rasterio resampling enum name.

    Returns:
        Float32 array shaped `(bands, tile_size, tile_size)`.

    Raises:
        ImportError: If rasterio is unavailable.
        AttributeError: If `resampling` is not a rasterio resampling method.
    """
    try:
        from rasterio.enums import Resampling
        from rasterio.transform import from_bounds
        from rasterio.warp import reproject
    except ImportError as exc:
        raise ImportError(
            "Python tiling requires rasterio. Install with "
            "`pip install mapwidgets[geospatial]`."
        ) from exc

    resampling_method = getattr(Resampling, resampling)
    dst_transform = from_bounds(*tile_bounds_3857(x, y, zoom), tile_size, tile_size)
    tile = np.full((len(bands), tile_size, tile_size), np.nan, dtype=np.float32)
    for index, band in enumerate(bands):
        reproject(
            source=dataset.read(band),
            destination=tile[index],
            src_transform=dataset.transform,
            src_crs=dataset.crs,
            src_nodata=dataset.nodata,
            dst_transform=dst_transform,
            dst_crs=WEB_MERCATOR_CRS,
            dst_nodata=np.nan,
            resampling=resampling_method,
        )
    return tile


def _render_tile(
    tile: np.ndarray,
    *,
    stretch_ranges: tuple[tuple[float, float], ...],
    transparent_values: Sequence[float] | None,
    transparent_ranges: Sequence[tuple[float | None, float | None]] | None,
    transparent_match: TransparentMatch,
    colormap: str | None,
) -> np.ndarray:
    """Convert tile band data into an RGBA uint8 image."""
    alpha = np.where(np.all(np.isfinite(tile), axis=0), 255, 0).astype(np.uint8)
    alpha = np.where(
        _transparent_mask(
            tile,
            transparent_values=transparent_values,
            transparent_ranges=transparent_ranges,
            transparent_match=transparent_match,
        ),
        0,
        alpha,
    )

    if colormap is not None:
        rgb = _apply_colormap(tile[0], stretch_ranges[0], colormap)
    else:
        channels = [
            _scale_band(tile[index], stretch_ranges[index])
            for index in _rgb_indexes(tile)
        ]
        rgb = np.stack(channels, axis=-1)

    rgba = np.zeros((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha
    return rgba


def _rgb_indexes(tile: np.ndarray) -> tuple[int, int, int]:
    """Return band indexes used for RGB rendering."""
    if tile.shape[0] == 1:
        return (0, 0, 0)
    if tile.shape[0] == 2:
        return (0, 1, 1)
    return (0, 1, 2)


def _scale_band(
    values: np.ndarray,
    value_range: tuple[float, float],
) -> np.ndarray:
    """Scale one numeric band to uint8 display values."""
    low, high = value_range
    scaled = (values - low) / (high - low)
    return (np.nan_to_num(np.clip(scaled, 0, 1), nan=0.0) * 255).astype(np.uint8)


def _apply_colormap(
    values: np.ndarray,
    value_range: tuple[float, float],
    colormap: str,
) -> np.ndarray:
    """Apply a Matplotlib colormap to one band."""
    try:
        from matplotlib import colormaps
    except ImportError as exc:
        raise ImportError(
            "Colormapped Python tiles require matplotlib. Install matplotlib "
            "or call from_tiled_geotiff(..., colormap=None)."
        ) from exc

    low, high = value_range
    normalized = np.clip((values - low) / (high - low), 0, 1)
    rgba = colormaps[colormap](np.nan_to_num(normalized, nan=0.0), bytes=True)
    return np.asarray(rgba[..., :3], dtype=np.uint8)


def _transparent_mask(
    tile: np.ndarray,
    *,
    transparent_values: Sequence[float] | None,
    transparent_ranges: Sequence[tuple[float | None, float | None]] | None,
    transparent_match: TransparentMatch,
) -> np.ndarray:
    """Return pixels hidden by exact values or numeric ranges."""
    masks: list[np.ndarray] = []
    if transparent_values is not None:
        values = np.asarray(tuple(transparent_values), dtype=float)
        masks.append(np.isin(tile, values))
    if transparent_ranges is not None:
        range_mask = np.zeros(tile.shape, dtype=bool)
        for lower, upper in transparent_ranges:
            current = np.ones(tile.shape, dtype=bool)
            if lower is not None:
                current &= tile >= lower
            if upper is not None:
                current &= tile <= upper
            range_mask |= current
        masks.append(range_mask)

    if not masks:
        return np.zeros(tile.shape[1:], dtype=bool)

    combined = np.logical_or.reduce(masks)
    if transparent_match == "any":
        return np.any(combined, axis=0)
    if transparent_match == "all":
        return np.all(combined, axis=0)
    raise ValueError("transparent_match must be 'any' or 'all'.")
