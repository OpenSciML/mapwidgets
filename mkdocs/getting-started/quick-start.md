# Quick Start

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

## Google Maps

Google Maps uses the same Python shape, but it requires a Maps JavaScript API
key:

```python
import os

from mapwidgets import MapViewer

viewer = (
    MapViewer(api_key=os.environ["GOOGLE_MAPS_API_KEY"], backend="google")
    .set_center(32.2207, -98.2023)
    .set_zoom(18)
)
```

## Add vector and raster layers

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

`VectorLayer.from_shapefile()` and `RasterLayer.from_tiled_geotiff()` require
the `geospatial` extra.
