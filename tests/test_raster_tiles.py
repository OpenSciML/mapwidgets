"""Raster tile backend tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace

import numpy as np
import rasterio
from rasterio.transform import from_origin
import pytest

from mapwidgets import RasterLayer, generate_geotiff_tiles
from mapwidgets._raster_tiles import gdal as gdal_tiles


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


def test_generate_geotiff_tiles_gdal_supports_older_gdal2tiles_signature(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GDAL 3.6 gdal2tiles.main does not accept called_from_main."""
    raster_path = tmp_path / "orthomosaic.tif"
    output_dir = tmp_path / "gdal_tiles"
    _write_rgb_geotiff(raster_path)
    calls: list[tuple[list[str], dict[str, object]]] = []
    subprocess_calls: list[list[str]] = []

    def fake_main(argv: list[str], **kwargs: object) -> None:
        calls.append((argv, kwargs))
        if "called_from_main" in kwargs:
            raise TypeError("main() got an unexpected keyword argument 'called_from_main'")
        raise AssertionError("old gdal2tiles.main must not be called in-process")

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        subprocess_calls.append(command)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is False
        (output_dir / "0" / "0").mkdir(parents=True)
        (output_dir / "0" / "0" / "0.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    fake_osgeo_utils = ModuleType("osgeo_utils")
    fake_osgeo_utils.gdal2tiles = SimpleNamespace(main=fake_main)
    monkeypatch.setitem(sys.modules, "osgeo_utils", fake_osgeo_utils)
    monkeypatch.setattr(gdal_tiles, "fill_missing_tiles", lambda *args, **kwargs: None)
    monkeypatch.setattr(gdal_tiles.subprocess, "run", fake_run)

    tiles_dir = gdal_tiles.generate_geotiff_tiles_gdal(
        raster_path,
        output_dir,
        zoom_levels=[0],
        tile_size=64,
        overwrite=True,
    )

    assert tiles_dir == output_dir
    assert len(calls) == 1
    assert calls[0][1] == {"called_from_main": False}
    assert subprocess_calls
    assert subprocess_calls[0][:3] == [sys.executable, "-m", "osgeo_utils.gdal2tiles"]
