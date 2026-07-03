# Layers

Layer classes are available from `mapwidgets` and `mapwidgets.layers`.

## `VectorLayer`

```python
from mapwidgets import VectorLayer

layer = VectorLayer.from_shapefile("plots.shp")
```

Dataclass fields:

- `id: str`
- `data: dict[str, Any]`
- `geometry: Literal["auto", "point", "line", "polygon"] = "auto"`
- `name: str | None = None`
- `fill_color: str = "#1f78ff"`
- `fill_opacity: float = 0.35`
- `stroke_color: str = "#1f78ff"`
- `stroke_opacity: float = 1.0`
- `stroke_width: int = 2`
- `circle_color: str = "#1f78ff"`
- `circle_radius: int = 5`
- `bounds: dict[str, float] | None = None`
- `properties: dict[str, Any]`

Methods:

- `VectorLayer.from_shapefile(path, **style_options)`
- `map_config()`
- `maplibre_config()`
- `google_maps_config()`

## `RasterLayer`

```python
from mapwidgets import RasterLayer

layer = RasterLayer.from_geotiff(
    "orthomosaic.tif",
    tiles_dir="orthomosaic_tiles",
    min_zoom=14,
    max_zoom=22,
)
```

Dataclass fields:

- `id: str`
- `base_url: str`
- `name: str | None = None`
- `min_zoom: int = 0`
- `max_zoom: int = 22`
- `tile_size: int = 256`
- `opacity: float = 1.0`
- `cache_key: str | None = None`
- `bounds: dict[str, float] | None = None`

Methods:

- `RasterLayer.from_geotiff(path, **options)`
- `RasterLayer.from_tiled_geotiff(path, **options)`
- `map_config()`
- `maplibre_config()`
- `google_maps_config()`
