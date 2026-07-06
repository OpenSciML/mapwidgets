# mapwidgets

PySide6 map widgets with interchangeable JavaScript map backends. The same
Python API can render with MapLibre GL JS or Google Maps JavaScript API.

## Install

Install the GUI extra when you want to open a desktop map viewer:

```bash
pip install "mapwidgets[pyside]"
```

Install the geospatial extra when you want to read Shapefiles or prepare
GeoTIFF tile pyramids:

```bash
pip install "mapwidgets[pyside,geospatial]"
```

The base package keeps the schema and layer objects lightweight. `PySide6`,
`GDAL`, `geopandas`, and `rasterio` are optional because they are heavier native
dependencies.

## Quick Start

Use `MapViewer` as the backend factory. Viewer methods return `self`, so common
setup can be written as a chain.

```python
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication

from mapwidgets import MapViewer, Marker

app = QApplication.instance() or QApplication([])

viewer = (
    MapViewer(backend="maplibre")
    .resize(QSize(900, 600))
    .set_center(32.2207, -98.2023)
    .set_zoom(15)
    .add_marker(
        Marker(
            position={"lat": 32.2207, "lng": -98.2023},
            title="Field",
        )
    )
    .show()
    .wait_for_map_ready()
)

app.exec()
```

Google Maps uses the same shape, but it requires a Maps JavaScript API key:

```python
import os

from mapwidgets import MapViewer

viewer = (
    MapViewer(api_key=os.environ["GOOGLE_MAPS_API_KEY"], backend="google")
    .set_center(32.2207, -98.2023)
    .set_zoom(18)
)
```

## Backends

`MapViewer` accepts these backend names:

- `maplibre`, `maplibre-gl`, `maplibre-gl-js`: MapLibre GL JS, no API key.
- `google`, `gmap`, `google-maps`: Google Maps JavaScript API, API key required.

You can also instantiate the concrete classes directly:

```python
from mapwidgets import GoogleMapViewer, MapLibreViewer

maplibre_viewer = MapLibreViewer()
google_viewer = GoogleMapViewer(api_key="...")
```

MapLibre-specific methods include `set_projection`, `set_pitch`, `set_bearing`,
and `add_terrain`. Google-specific methods include `set_tilt` and `set_heading`.

## Elements

Basic map elements are backend-neutral Pydantic models.

```python
from mapwidgets import Marker, Polygon, Polyline

viewer.add_marker(
    Marker(position={"lat": 32.2207, "lng": -98.2023}, title="Sample")
)

viewer.add_polyline(
    Polyline(
        path=[
            {"lat": 32.2207, "lng": -98.2023},
            {"lat": 32.2212, "lng": -98.2015},
        ],
        strokeColor="#0f766e",
        strokeWeight=3,
    )
)

viewer.add_polygon(
    Polygon(
        paths=[
            {"lat": 32.2207, "lng": -98.2023},
            {"lat": 32.2212, "lng": -98.2020},
            {"lat": 32.2209, "lng": -98.2015},
        ],
        fillColor="#2563eb",
        fillOpacity=0.35,
    )
)
```

Elements can carry custom application data in `properties`. Register an element
click callback to receive those properties when a marker, polyline, or polygon
is clicked:

```python
from mapwidgets import MapViewer, Marker


def handle_element_click(element_type: str, payload: dict) -> None:
    print(element_type, payload["properties"])


viewer = (
    MapViewer(backend="maplibre")
    .on_element_click(handle_element_click)
    .add_marker(
        Marker(
            position={"lat": 32.2207, "lng": -98.2023},
            title="Plot 12",
            properties={
                "plot_id": "P12",
                "crop": "peanut",
                "treatment": "irrigated",
            },
        )
    )
)
```

The click payload includes `properties` with your custom data and `element` with
the original marker, polyline, or polygon configuration.

## Layers

`RasterLayer` and `VectorLayer` provide a backend-neutral layer interface.

```python
from mapwidgets import MapViewer, RasterLayer, VectorLayer

plots = VectorLayer.from_shapefile("plots.shp")
orthomosaic = RasterLayer.from_tiled_geotiff(
    "orthomosaic.tif",
    min_zoom=14,
    max_zoom=22,
    backend="gdal",
)

viewer = (
    MapViewer(backend="maplibre")
    .add_layer(orthomosaic, zoom_to=True, max_zoom=22)
    .add_layer(plots, zoom_to=True, max_zoom=18)
)
```

Vector layers expect EPSG:4326 longitude/latitude coordinates in the browser.
`VectorLayer.from_shapefile()` reprojects Shapefiles with CRS metadata when the
geospatial dependencies are installed.

Raster layers are rendered as XYZ PNG tiles. `RasterLayer.from_geotiff()` does
not stream a raw TIFF into the browser; it points at an existing tile pyramid:

```python
layer = RasterLayer.from_geotiff(
    "orthomosaic.tif",
    tiles_dir="orthomosaic_tiles",
    min_zoom=14,
    max_zoom=22,
)
viewer.add_layer(layer, zoom_to=True, max_zoom=22)
```

Use higher tile zooms for high-resolution drone orthomosaics. If tiles are only
generated to z16 and the map is zoomed to z20, the browser stretches the z16
imagery and the result will look blurry.

## GeoTIFF Tiling

For large orthomosaics, prepare the TIFF for tiling and generate browser-ready
tiles before adding it to the map.

```python
from mapwidgets import generate_geotiff_tiles, optimize_geotiff_for_tiling

optimized = optimize_geotiff_for_tiling("orthomosaic.tif")
tiles_dir = generate_geotiff_tiles(
    optimized,
    min_zoom=14,
    max_zoom=22,
)
```

Then load the generated folder:

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_geotiff(
    "orthomosaic.tif",
    tiles_dir=tiles_dir,
    min_zoom=14,
    max_zoom=22,
)
```

For the common case, `from_tiled_geotiff()` runs the same preparation step and
returns the layer object. Use `backend="gdal"` for source-order RGB GeoTIFFs:

```python
layer = RasterLayer.from_tiled_geotiff(
    "orthomosaic.tif",
    min_zoom=14,
    max_zoom=22,
    backend="gdal",
    overwrite=False,
)
```

Use `backend="python"` when you need arbitrary band selections, colormaps, or
transparent value/range masks:

```python
layer = RasterLayer.from_tiled_geotiff(
    "multispectral_orthomosaic.tif",
    output_dir=".mapwidgets_tiles/false_color",
    bands=(6, 4, 2),
    zoom_levels=range(18, 22),
    backend="python",
    overwrite=True,
)
```

The tiling helper:

- creates an optimized GeoTIFF suitable for tiling;
- runs the selected backend with XYZ tile coordinates;
- writes tile metadata;
- fills missing edge tiles with transparent PNGs so MapLibre does not spam tile
  errors outside the raster footprint;
- reuses an existing complete tile folder when `overwrite=False`.

Keep `max_zoom` realistic. Very high zoom levels can create a large number of
tiles, so the helper estimates tile counts and stops before generating an
unexpectedly huge pyramid.

## Zooming

You can zoom to bounds directly:

```python
viewer.fit_bounds(
    {"west": -98.204, "south": 32.219, "east": -98.200, "north": 32.223},
    padding=48,
    max_zoom=18,
)
```

You can also zoom to a layer at add time:

```python
viewer.add_layer(plots, zoom_to=True, max_zoom=18)
```

Or later:

```python
viewer.add_layer(plots).zoom_to_layer(plots, max_zoom=18)
```

`max_zoom` caps the final zoom after the map fits the layer bounds. This is
useful for small plot polygons or high-resolution rasters where the automatic
fit may zoom in too far.

## Current Location

`center_on_current_location()` centers the map using an IP-based location lookup
from Python:

```python
viewer.center_on_current_location(zoom=14, add_marker=True)
```

This avoids macOS application bundle permission requirements for Qt location
services, but IP location is approximate and may be wrong by city or network
region. For field-grade accuracy, pass coordinates from GPS hardware or another
trusted location source to `set_center()`.

## Terrain

Terrain is currently a MapLibre feature:

```python
from mapwidgets import MapLibreViewer

viewer = (
    MapLibreViewer()
    .set_projection("mercator")
    .add_terrain(
        url="https://example.com/terrain/tiles.json",
        encoding="terrarium",
        exaggeration=1.5,
    )
)
```

Use a terrain-raster source compatible with MapLibre, such as Terrarium or
Mapbox-style RGB elevation tiles. Globe projection and terrain have limitations
in MapLibre, so use `mercator` when validating terrain rendering.

## Development

Run a quick syntax check with:

```bash
uv run .venv/bin/python -m compileall main.py src
```
