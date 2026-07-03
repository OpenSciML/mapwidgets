# mapwidgets

`mapwidgets` provides PySide6 map viewers with interchangeable JavaScript map
backends. The same Python API can render interactive desktop maps with
MapLibre GL JS or the Google Maps JavaScript API.

The library keeps the core schema objects lightweight and makes GUI and
geospatial dependencies optional. Install only the extras needed for the
workflow you are running.

## What it provides

- A `MapViewer` factory for choosing `maplibre` or `google` at runtime.
- Concrete `MapLibreViewer` and `GoogleMapViewer` classes for backend-specific
  behavior.
- Pydantic element models for markers, polylines, polygons, circles, and
  rectangles.
- Backend-neutral `RasterLayer` and `VectorLayer` objects.
- GeoTIFF helpers for preparing XYZ PNG tile pyramids from orthomosaics and
  other georeferenced rasters.

## Minimal example

```python
from PySide6.QtWidgets import QApplication

from mapwidgets import MapViewer, Marker

app = QApplication.instance() or QApplication([])

viewer = (
    MapViewer(backend="maplibre")
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

## Documentation map

- Start with [Installation](getting-started/installation.md) and
  [Quick Start](getting-started/quick-start.md).
- Use [Backends](getting-started/backends.md) when choosing between MapLibre
  and Google Maps.
- Use [Layers](guides/layers.md) and [GeoTIFF Tiling](guides/geotiff-tiling.md)
  for Shapefiles, GeoJSON, orthomosaics, and raster tile pyramids.
- Use the [API reference](api/index.md) for import paths and method summaries.
