# Raster Tiles

Raster tiling helpers are defined in `mapwidgets.raster_tiles` and exported
from the top-level package.

## `optimize_geotiff_for_tiling(input_path, output_path=None, **options)`

Creates a tiled COG-style GeoTIFF optimized for web tile generation.

Common options:

- `overwrite=False`
- `block_size=512`
- `compress="DEFLATE"`
- `resampling="AVERAGE"`
- `num_threads="ALL_CPUS"`

Returns the optimized GeoTIFF path.

## `generate_geotiff_tiles(input_path, output_dir=None, **options)`

Generates XYZ PNG tiles from a georeferenced GeoTIFF and returns the tile
folder. Use `backend="gdal"` for `osgeo_utils.gdal2tiles` or
`backend="python"` for rasterio-based rendering.

Common options:

- `backend="gdal"`
- `bands=(1, 2, 3)`
- `min_zoom=None`
- `max_zoom=None`
- `zoom_levels=None`
- `tile_size=256`
- `overwrite=False`
- `max_tiles=20_000`
- `processes=None`
- `resampling="bilinear"`
- `name=None`
- `opacity=1.0`
- `stretch_method="percentiles"`
- `transparent_values=(0,)`
- `transparent_ranges=None`
- `transparent_match="any"`
- `colormap=None`
- `value_range=None`
- `stretch_sample_size=1024`

## `prepare_geotiff_tiles(input_path, output_dir=None, **options)`

Optionally optimizes a GeoTIFF and generates XYZ PNG tiles from the selected
backend. This is the helper used by `RasterLayer.from_tiled_geotiff()`.

## `validate_tile_directory(tiles_dir, bounds, min_zoom, max_zoom, tile_size=256)`

Validates that expected XYZ tile files exist for the given bounds and zoom
range.

## `fill_missing_tiles(tiles_dir, bounds, min_zoom, max_zoom, tile_size=256)`

Writes transparent PNGs for missing XYZ tiles inside the layer bounds and
returns the number of generated placeholder tiles.
