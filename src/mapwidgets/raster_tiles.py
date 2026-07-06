"""Utilities for preparing GeoTIFFs and generating web map tiles."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from ._raster_tiles.common import (
    DEFAULT_TILE_SIZE,
    TileBackend,
    TransparentMatch,
    fill_missing_tiles,
    optimize_geotiff_for_tiling,
    validate_tile_directory,
)
from ._raster_tiles.gdal import generate_geotiff_tiles_gdal
from ._raster_tiles.python import generate_geotiff_tiles_python


def generate_geotiff_tiles(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    backend: TileBackend = "gdal",
    bands: Sequence[int] = (1, 2, 3),
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
    stretch_method: str = "percentiles",
    transparent_values: Sequence[float] | None = (0,),
    transparent_ranges: Sequence[tuple[float | None, float | None]] | None = None,
    transparent_match: TransparentMatch = "any",
    colormap: str | None = None,
    value_range: tuple[float, float] | None = None,
    stretch_sample_size: int = 1024,
) -> Path:
    """Generate XYZ PNG tiles from a georeferenced GeoTIFF and return the folder.

    The ``gdal`` backend uses ``osgeo_utils.gdal2tiles`` and is the fastest
    path for file-backed RGB rasters. The ``python`` backend uses rasterio and
    supports selected bands, false-color colormaps, and transparency masks.

    Args:
        input_path: Source GeoTIFF path.
        output_dir: Directory where `{z}/{x}/{y}.png` tiles are written.
        backend: Tile renderer, either ``"gdal"`` or ``"python"``.
        bands: One-based source bands used by the Python backend.
        min_zoom: Minimum generated zoom when `zoom_levels` is omitted.
        max_zoom: Maximum generated zoom when `zoom_levels` is omitted.
        zoom_levels: Explicit zoom levels to generate.
        tile_size: Pixel width and height for generated square tiles.
        overwrite: Whether to replace an existing tile folder.
        max_tiles: Safety limit for generated tile count.
        processes: GDAL worker process count.
        resampling: Backend resampling method name.
        name: Layer name written to metadata.
        opacity: Raster opacity written to metadata.
        stretch_method: Python backend display scaling method.
        transparent_values: Exact source values hidden by the Python backend.
        transparent_ranges: Inclusive source value ranges hidden by the Python
            backend.
        transparent_match: Whether transparency applies when any or all
            selected bands match.
        colormap: Optional Matplotlib colormap for Python single-band rendering.
        value_range: Optional `(min, max)` normalization range.
        stretch_sample_size: Maximum sampled width or height used by the Python
            backend to estimate display ranges.

    Returns:
        Tile output directory.

    Raises:
        ValueError: If the backend or backend-specific options are invalid.
        FileNotFoundError: If `input_path` does not exist.
    """
    if backend == "gdal":
        if tuple(bands) not in {(1,), (1, 2), (1, 2, 3)}:
            raise ValueError(
                "The GDAL backend can only render the source band order. "
                "Use backend='python' for arbitrary band selections."
            )
        if colormap is not None or transparent_ranges is not None:
            raise ValueError(
                "The GDAL backend does not support colormaps or transparent "
                "ranges. Use backend='python'."
            )
        return generate_geotiff_tiles_gdal(
            input_path,
            output_dir,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            zoom_levels=zoom_levels,
            tile_size=tile_size,
            overwrite=overwrite,
            max_tiles=max_tiles,
            processes=processes,
            resampling=resampling,
            name=name,
            opacity=opacity,
        )
    if backend == "python":
        return generate_geotiff_tiles_python(
            input_path,
            output_dir,
            bands=bands,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            zoom_levels=zoom_levels,
            tile_size=tile_size,
            overwrite=overwrite,
            max_tiles=max_tiles,
            resampling=resampling,
            name=name,
            opacity=opacity,
            stretch_method=stretch_method,  # type: ignore[arg-type]
            transparent_values=transparent_values,
            transparent_ranges=transparent_ranges,
            transparent_match=transparent_match,
            colormap=colormap,
            value_range=value_range,
            stretch_sample_size=stretch_sample_size,
        )
    raise ValueError("backend must be 'gdal' or 'python'.")


def prepare_geotiff_tiles(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    *,
    backend: TileBackend = "gdal",
    optimized_path: str | Path | None = None,
    optimize: bool = True,
    overwrite: bool = False,
    bands: Sequence[int] = (1, 2, 3),
    min_zoom: int | None = None,
    max_zoom: int | None = None,
    zoom_levels: Iterable[int] | None = None,
    tile_size: int = DEFAULT_TILE_SIZE,
    max_tiles: int = 20_000,
    processes: int | None = None,
    resampling: str = "bilinear",
    name: str | None = None,
    opacity: float = 1.0,
    stretch_method: str = "percentiles",
    transparent_values: Sequence[float] | None = (0,),
    transparent_ranges: Sequence[tuple[float | None, float | None]] | None = None,
    transparent_match: TransparentMatch = "any",
    colormap: str | None = None,
    value_range: tuple[float, float] | None = None,
    stretch_sample_size: int = 1024,
) -> Path:
    """Optionally optimize a GeoTIFF and generate XYZ tiles.

    Args:
        input_path: Source GeoTIFF path.
        output_dir: Directory where `{z}/{x}/{y}.png` tiles are written.
        backend: Tile renderer, either ``"gdal"`` or ``"python"``.
        optimized_path: Destination path for the optional optimized GeoTIFF.
        optimize: Whether to create a tiled COG-style GeoTIFF before tiling.
        overwrite: Whether to replace existing optimized files or tile folders.
        bands: One-based source bands used by the Python backend.
        min_zoom: Minimum generated zoom when `zoom_levels` is omitted.
        max_zoom: Maximum generated zoom when `zoom_levels` is omitted.
        zoom_levels: Explicit zoom levels to generate.
        tile_size: Pixel width and height for generated square tiles.
        max_tiles: Safety limit for generated tile count.
        processes: GDAL worker process count.
        resampling: Backend resampling method name.
        name: Layer name written to metadata.
        opacity: Raster opacity written to metadata.
        stretch_method: Python backend display scaling method.
        transparent_values: Exact source values hidden by the Python backend.
        transparent_ranges: Inclusive source value ranges hidden by the Python
            backend.
        transparent_match: Whether transparency applies when any or all
            selected bands match.
        colormap: Optional Matplotlib colormap for Python single-band rendering.
        value_range: Optional `(min, max)` normalization range.
        stretch_sample_size: Maximum sampled width or height used by the Python
            backend to estimate display ranges.

    Returns:
        Tile output directory.

    Raises:
        FileNotFoundError: If `input_path` does not exist.
        RuntimeError: If optimization or the selected backend fails.
        ValueError: If backend-specific options are invalid.
    """
    source = Path(input_path)
    if optimize:
        source = optimize_geotiff_for_tiling(
            source,
            optimized_path,
            overwrite=overwrite,
        )
    return generate_geotiff_tiles(
        source,
        output_dir,
        backend=backend,
        bands=bands,
        min_zoom=min_zoom,
        max_zoom=max_zoom,
        zoom_levels=zoom_levels,
        tile_size=tile_size,
        overwrite=overwrite,
        max_tiles=max_tiles,
        processes=processes,
        resampling=resampling,
        name=name,
        opacity=opacity,
        stretch_method=stretch_method,
        transparent_values=transparent_values,
        transparent_ranges=transparent_ranges,
        transparent_match=transparent_match,
        colormap=colormap,
        value_range=value_range,
        stretch_sample_size=stretch_sample_size,
    )


__all__ = [
    "fill_missing_tiles",
    "generate_geotiff_tiles",
    "generate_geotiff_tiles_gdal",
    "generate_geotiff_tiles_python",
    "optimize_geotiff_for_tiling",
    "prepare_geotiff_tiles",
    "validate_tile_directory",
]
