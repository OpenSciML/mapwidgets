# GeoTIFF Tiling

For large orthomosaics, prepare the TIFF for tiling and generate browser-ready
XYZ PNG tiles before adding it to the map.

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

## One-step helper

For the common case, `from_tiled_geotiff()` runs the same preparation step and
returns a `RasterLayer` object:

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_tiled_geotiff(
    "orthomosaic.tif",
    min_zoom=14,
    max_zoom=22,
    overwrite=False,
)
```

## What the tiling helper does

The tiling helper:

- creates an optimized GeoTIFF suitable for tiling;
- runs `gdal2tiles` with XYZ tile coordinates;
- writes `metadata.json` next to the tiles;
- fills missing edge tiles with transparent PNGs so MapLibre does not report
  repeated tile errors outside the raster footprint;
- reuses an existing complete tile folder when `overwrite=False`.

## Zoom level guidance

Use higher tile zooms for high-resolution drone orthomosaics. If tiles are only
generated to z16 and the map is zoomed to z20, the browser stretches the z16
imagery and the result will look blurry.

Keep `max_zoom` realistic. Very high zoom levels can create a large number of
tiles, so the helper estimates tile counts and stops before generating an
unexpectedly large pyramid. Increase `max_tiles` only after confirming that the
tile count is appropriate for the raster size and storage budget.
