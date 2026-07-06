# GeoTIFF Tiling

For large orthomosaics, prepare the TIFF for tiling and generate browser-ready
XYZ PNG tiles before adding it to the map.

Mapwidgets owns raster tile generation. Use `RasterLayer.from_tiled_geotiff()`
for the common path, or call the lower-level helpers in `mapwidgets.raster_tiles`
when you need to separate optimization from tile generation.

## Backends

Two tile backends are available:

- `backend="gdal"` uses `osgeo_utils.gdal2tiles`. It is the fastest path for
  file-backed source-order RGB GeoTIFFs.
- `backend="python"` uses rasterio. It supports arbitrary one-based band
  selections, colormaps, value ranges, and transparent value/range masks.

## One-Step Helper

For normal RGB rasters, use the GDAL backend:

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_tiled_geotiff(
    "orthomosaic.tif",
    output_dir=".mapwidgets_tiles/rgb",
    bands=(1, 2, 3),
    min_zoom=14,
    max_zoom=22,
    backend="gdal",
    overwrite=False,
)
```

For multispectral false-color display, use the Python backend:

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_tiled_geotiff(
    "multispectral_orthomosaic.tif",
    output_dir=".mapwidgets_tiles/false_color",
    bands=(6, 4, 2),
    zoom_levels=range(18, 22),
    backend="python",
    overwrite=True,
)
```

For a single-band index GeoTIFF, use a colormap and explicit value range:

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_tiled_geotiff(
    "ndvi.tif",
    output_dir=".mapwidgets_tiles/ndvi",
    bands=(1,),
    zoom_levels=range(18, 22),
    backend="python",
    colormap="RdYlGn",
    value_range=(-1.0, 1.0),
    transparent_ranges=((-1.0, 0.0),),
    transparent_values=None,
    overwrite=True,
)
```

Add the returned layer to any mapwidgets viewer:

```python
import sys

from mapwidgets import MapViewer
from PySide6.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv[:1])
viewer = MapViewer(backend="maplibre").resize(1200, 800).show()
viewer.add_layer(layer, zoom_to=True)
viewer.wait_for_map_ready()
app.exec()
```

## Separate Optimization And Tiling

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

## What the tiling helper does

The tiling helper:

- creates an optimized GeoTIFF suitable for tiling;
- runs the selected backend with XYZ tile coordinates;
- writes `metadata.json` next to the tiles;
- fills missing edge tiles with transparent PNGs so MapLibre does not report
  repeated tile errors outside the raster footprint;
- reuses an existing complete tile folder when `overwrite=False`.

## Huge Rasters

Very large orthomosaics need a preparation step before tile generation. A 10 GB
raster stored as scanline strips without internal overviews can be slow because
every map tile may require expensive random reads from the original image.

`RasterLayer.from_tiled_geotiff(..., optimize=True)` and
`prepare_geotiff_tiles(..., optimize=True)` create a Cloud Optimized GeoTIFF
before tiling. The optimization uses practical GDAL defaults:

- `BIGTIFF=IF_SAFER` allows output files larger than 4 GB when needed.
- `COMPRESS=DEFLATE` applies lossless compression.
- `BLOCKSIZE=512` stores the raster in internal 512 x 512 tiles.
- `OVERVIEWS=AUTO` builds lower-resolution internal pyramids.
- `NUM_THREADS=ALL_CPUS` lets GDAL use all CPU cores during conversion.

The conversion preserves pixel size, width, height, CRS, bounds, and bands
unless you pass explicit resampling options.

## Zoom level guidance

Use higher tile zooms for high-resolution drone orthomosaics. If tiles are only
generated to z16 and the map is zoomed to z20, the browser stretches the z16
imagery and the result will look blurry.

Keep `max_zoom` realistic. Very high zoom levels can create a large number of
tiles, so the helper estimates tile counts and stops before generating an
unexpectedly large pyramid. Increase `max_tiles` only after confirming that the
tile count is appropriate for the raster size and storage budget.
