"""Raster map layer models."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ._utils import file_base_url, read_geotiff_bounds, validate_lnglat_bounds


@dataclass
class RasterLayer:
    """Raster tile layer consumed by map viewer backends.

    Use `RasterLayer` when the browser should display an XYZ PNG tile pyramid.
    The raw GeoTIFF is not streamed to the browser; construct layers from an
    existing tile directory with `from_geotiff()` or generate tiles first with
    `from_tiled_geotiff()`.

    Attributes:
        id: Stable layer id used by the frontend.
        base_url: Tile root URL without `/{z}/{x}/{y}.png`.
        name: Human-readable layer name.
        min_zoom: Minimum available tile zoom.
        max_zoom: Maximum available tile zoom.
        tile_size: Tile width and height in pixels.
        opacity: Raster opacity in the inclusive range 0-1.
        cache_key: Optional cache-busting query value.
        bounds: Optional WGS84 bounds with `north`, `south`, `east`, and `west`.
    """

    id: str
    base_url: str
    name: str | None = None
    min_zoom: int = 0
    max_zoom: int = 22
    tile_size: int = 256
    opacity: float = 1.0
    cache_key: str | None = None
    bounds: dict[str, float] | None = None

    @classmethod
    def from_geotiff(
        cls,
        path: str | Path,
        *,
        id: str | None = None,
        name: str | None = None,
        base_url: str | None = None,
        tiles_dir: str | Path | None = None,
        min_zoom: int = 0,
        max_zoom: int = 22,
        tile_size: int = 256,
        opacity: float = 1.0,
        cache_key: str | None = None,
        bounds: dict[str, float] | None = None,
        validate_tiles: bool = True,
    ) -> RasterLayer:
        """Create a raster layer config for GeoTIFF-derived XYZ tiles.

        Parameters
        ----------
        path
            Source GeoTIFF path. The raw TIFF is not read by the browser; by
            default this expects tiles in a sibling folder named after the TIFF
            stem, for example ``orthomosaic/{z}/{x}/{y}.png``.
        id
            Layer id used by the frontend.
        name
            Human-readable layer name.
        base_url
            Explicit XYZ tile base URL without ``/{z}/{x}/{y}.png``.
        tiles_dir
            Local static XYZ tile directory. Overrides the default sibling
            folder convention when ``base_url`` is not provided.
        min_zoom
            Minimum tile zoom.
        max_zoom
            Maximum tile zoom.
        tile_size
            Tile size in pixels.
        opacity
            Raster opacity.
        cache_key
            Optional cache-busting query value.
        bounds
            Optional layer bounds as ``north``, ``south``, ``east``, and
            ``west``. If omitted, rasterio is used when available.
        validate_tiles
            Whether to verify the expected local tile directory exists when
            using local tiles.
        """
        geotiff_path = Path(path)
        layer_id = id or geotiff_path.stem
        if base_url is None:
            tile_path = Path(tiles_dir) if tiles_dir else geotiff_path.with_suffix("")
            if validate_tiles and not tile_path.expanduser().exists():
                raise FileNotFoundError(
                    "RasterLayer.from_geotiff() displays XYZ PNG tiles, not the "
                    f"raw GeoTIFF. Expected tile directory at {tile_path}. "
                    "Generate tiles first, pass tiles_dir=..., or pass base_url=..."
                )
            base_url = file_base_url(tile_path)

        return cls(
            id=layer_id,
            name=name or layer_id,
            base_url=base_url.rstrip("/"),
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            tile_size=tile_size,
            opacity=opacity,
            cache_key=cache_key,
            bounds=validate_lnglat_bounds(bounds) or read_geotiff_bounds(geotiff_path),
        )

    @classmethod
    def from_tiled_geotiff(
        cls,
        path: str | Path,
        *,
        output_dir: str | Path | None = None,
        backend: Literal["gdal", "python"] = "gdal",
        bands: Sequence[int] = (1, 2, 3),
        optimize: bool = True,
        optimized_path: str | Path | None = None,
        overwrite: bool = False,
        min_zoom: int | None = None,
        max_zoom: int | None = None,
        zoom_levels: Iterable[int] | None = None,
        id: str | None = None,
        name: str | None = None,
        tile_size: int = 256,
        opacity: float = 1.0,
        max_tiles: int = 20_000,
        processes: int | None = None,
        resampling: str = "bilinear",
        stretch_method: str = "percentiles",
        transparent_values: Sequence[float] | None = (0,),
        transparent_ranges: Sequence[tuple[float | None, float | None]] | None = None,
        transparent_match: Literal["any", "all"] = "any",
        colormap: str | None = None,
        value_range: tuple[float, float] | None = None,
        stretch_sample_size: int = 1024,
    ) -> RasterLayer:
        """Generate XYZ tiles from a GeoTIFF and return a raster layer.

        Parameters
        ----------
        path
            Source GeoTIFF path.
        output_dir
            Directory where XYZ tiles are written.
        backend
            Tile renderer. ``"gdal"`` uses ``osgeo_utils.gdal2tiles``.
            ``"python"`` uses rasterio and supports selected bands,
            colormaps, and transparent value/range masks.
        bands
            One-based source bands used by the Python backend. The GDAL
            backend supports source-order bands only.
        optimize
            Whether to create an optimized COG before tiling.
        optimized_path
            Optional output path for the optimized COG.
        overwrite
            Whether to replace existing optimized files or tile folders.
        min_zoom
            Minimum generated zoom.
        max_zoom
            Maximum generated zoom.
        zoom_levels
            Explicit zoom levels to generate.
        id
            Layer id used by the frontend.
        name
            Human-readable layer name.
        tile_size
            Tile size in pixels.
        opacity
            Raster opacity.
        max_tiles
            Safety limit for generated tile count.
        processes
            Number of GDAL worker processes.
        resampling
            Resampling method used by the selected backend.
        stretch_method
            Python backend display scaling method: ``"percentiles"`` or
            ``"linear"``.
        transparent_values
            Exact source values hidden by the Python backend.
        transparent_ranges
            Inclusive value ranges hidden by the Python backend.
        transparent_match
            Whether transparency applies when ``"any"`` or ``"all"`` selected
            bands match.
        colormap
            Optional Matplotlib colormap for single-band Python rendering.
        value_range
            Optional normalization range used by the Python backend.
        stretch_sample_size
            Maximum sample width or height used to estimate display ranges.
        """
        from mapwidgets.raster_tiles import prepare_geotiff_tiles

        geotiff_path = Path(path)
        tiles_dir = prepare_geotiff_tiles(
            geotiff_path,
            output_dir,
            backend=backend,
            optimized_path=optimized_path,
            optimize=optimize,
            overwrite=overwrite,
            bands=bands,
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            zoom_levels=zoom_levels,
            tile_size=tile_size,
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

        metadata_path = tiles_dir / "metadata.json"
        metadata = (
            json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        )

        return cls.from_geotiff(
            geotiff_path,
            id=id,
            name=name or metadata.get("name"),
            tiles_dir=tiles_dir,
            min_zoom=metadata.get("minZoom", min_zoom or 0),
            max_zoom=metadata.get("maxZoom", max_zoom or 22),
            tile_size=tile_size,
            opacity=opacity,
            bounds=metadata.get("bounds"),
        )

    def map_config(self) -> dict[str, Any]:
        """Return a backend-neutral raster layer config."""
        return {
            "type": "raster",
            "id": self.id,
            "name": self.name,
            "baseUrl": self.base_url,
            "minZoom": self.min_zoom,
            "maxZoom": self.max_zoom,
            "tileSize": self.tile_size,
            "opacity": self.opacity,
            "cacheKey": self.cache_key,
            "bounds": validate_lnglat_bounds(self.bounds),
        }

    def maplibre_config(self) -> dict[str, Any]:
        """Return a MapLibre raster layer config."""
        return self.map_config()

    def google_maps_config(self) -> dict[str, Any]:
        """Return a Google Maps raster overlay config."""
        return self.map_config()
