# API Reference

The top-level `mapwidgets` package exports the main viewer classes, element
schemas, layer classes, and raster tiling helpers.

```python
from mapwidgets import (
    BaseMapViewer,
    GoogleMapViewer,
    MapLibreViewer,
    MapViewer,
    Marker,
    Polygon,
    Polyline,
    RasterLayer,
    VectorLayer,
    generate_geotiff_tiles,
    generate_geotiff_tiles_gdal,
    generate_geotiff_tiles_python,
    optimize_geotiff_for_tiling,
    prepare_geotiff_tiles,
)
```

GUI classes are imported lazily so the core schema objects can be used without
installing PySide6.

## Modules

| Module | Public surface |
| --- | --- |
| `mapwidgets.map_viewer` | `MapViewer`, `BaseMapViewer`, `MapLibreViewer`, `GoogleMapViewer` |
| `mapwidgets.map_elements` | `Point`, `Marker`, `Polyline`, `Polygon`, `Circle`, `RectangleBounds`, `Rectangle` |
| `mapwidgets.layers` | `RasterLayer`, `VectorLayer` |
| `mapwidgets.raster_tiles` | `optimize_geotiff_for_tiling`, `generate_geotiff_tiles`, `generate_geotiff_tiles_gdal`, `generate_geotiff_tiles_python`, `prepare_geotiff_tiles`, `validate_tile_directory`, `fill_missing_tiles` |
