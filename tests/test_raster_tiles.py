"""Raster tile backend tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from mapwidgets import RasterLayer, generate_geotiff_tiles


def _write_rgb_geotiff(path: Path) -> None:
    """Write a tiny georeferenced RGB GeoTIFF for tile tests."""
    profile = {
        "driver": "GTiff",
        "height": 8,
        "width": 8,
        "count": 3,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": from_origin(-98.0, 32.0008, 0.0001, 0.0001),
    }
    data = np.stack(
        [
            np.full((8, 8), 100, dtype=np.uint8),
            np.full((8, 8), 120, dtype=np.uint8),
            np.full((8, 8), 140, dtype=np.uint8),
        ]
    )
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(data)


def test_generate_geotiff_tiles_python_creates_xyz_pngs(tmp_path: Path) -> None:
    """Confirm the Python backend creates a valid XYZ tile folder."""
    raster_path = tmp_path / "orthomosaic.tif"
    output_dir = tmp_path / "tiles"
    _write_rgb_geotiff(raster_path)

    tiles_dir = generate_geotiff_tiles(
        raster_path,
        output_dir,
        backend="python",
        zoom_levels=[0],
        tile_size=64,
        overwrite=True,
        transparent_values=None,
    )

    tile_path = tiles_dir / "0" / "0" / "0.png"
    metadata = json.loads((tiles_dir / "metadata.json").read_text())

    assert tile_path.exists()
    assert tile_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert metadata["minZoom"] == 0
    assert metadata["maxZoom"] == 0
    assert metadata["tileSize"] == 64
    assert metadata["baseUrl"].startswith("file://")


def test_raster_layer_from_tiled_geotiff_supports_python_backend(
    tmp_path: Path,
) -> None:
    """Confirm RasterLayer delegates tile generation to the selected backend."""
    raster_path = tmp_path / "orthomosaic.tif"
    output_dir = tmp_path / "layer_tiles"
    _write_rgb_geotiff(raster_path)

    layer = RasterLayer.from_tiled_geotiff(
        raster_path,
        output_dir=output_dir,
        backend="python",
        optimize=False,
        zoom_levels=[0],
        tile_size=64,
        overwrite=True,
        transparent_values=None,
    )

    assert layer.base_url == output_dir.resolve().as_uri()
    assert layer.min_zoom == 0
    assert layer.max_zoom == 0
    assert layer.tile_size == 64
    assert (output_dir / "0" / "0" / "0.png").exists()
