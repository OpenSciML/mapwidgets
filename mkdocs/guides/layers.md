# Layers

`RasterLayer` and `VectorLayer` provide a backend-neutral layer interface. A
viewer chooses the backend-specific config by calling `maplibre_config()`,
`google_maps_config()`, or `map_config()`.

## Vector layers

`VectorLayer.from_shapefile()` reads a Shapefile into GeoJSON and computes
browser-ready bounds when possible.

```python
from mapwidgets import VectorLayer

plots = VectorLayer.from_shapefile(
    "plots.shp",
    fill_color="#22c55e",
    stroke_color="#14532d",
    stroke_width=2,
)

viewer.add_layer(plots, zoom_to=True, max_zoom=18)
```

Vector layers expect EPSG:4326 longitude/latitude coordinates in the browser.
`VectorLayer.from_shapefile()` reprojects Shapefiles with CRS metadata when the
geospatial dependencies are installed.

## Raster layers

Raster layers are rendered as XYZ PNG tiles. `RasterLayer.from_geotiff()` does
not stream a raw TIFF into the browser; it points at an existing tile pyramid.

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_geotiff(
    "orthomosaic.tif",
    tiles_dir="orthomosaic_tiles",
    min_zoom=14,
    max_zoom=22,
)

viewer.add_layer(layer, zoom_to=True, max_zoom=22)
```

Use `base_url` when the tiles are served from a web server instead of a local
directory:

```python
layer = RasterLayer.from_geotiff(
    "orthomosaic.tif",
    base_url="https://example.com/tiles/orthomosaic",
    min_zoom=14,
    max_zoom=22,
    validate_tiles=False,
)
```

## Zooming to layers

You can zoom to a layer when adding it:

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
