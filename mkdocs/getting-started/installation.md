# Installation

Install the GUI extra when you want to open a desktop map viewer:

```bash
pip install "mapwidgets[pyside]"
```

Install the geospatial extra when you want to read Shapefiles or prepare
GeoTIFF tile pyramids:

```bash
pip install "mapwidgets[pyside,geospatial]"
```

The base package depends on Pydantic and `python-dotenv`. `PySide6`, GDAL,
GeoPandas, and rasterio are optional because they are heavier native
dependencies and are only needed for specific workflows.

## Extras

| Extra | Installs | Use when |
| --- | --- | --- |
| `pyside` | `PySide6` | Opening a desktop map viewer with Qt WebEngine. |
| `geospatial` | `gdal`, `geopandas`, `rasterio` | Reading Shapefiles, reading GeoTIFF bounds, or generating XYZ raster tiles. |

## Development environment

This repository uses `uv`. To install the docs dependencies in a local checkout:

```bash
uv sync --group docs
```

To run a quick syntax check:

```bash
uv run .venv/bin/python -m compileall main.py src
```
