# Backends

`MapViewer` accepts these backend names:

| Backend | Aliases | API key |
| --- | --- | --- |
| MapLibre GL JS | `maplibre`, `maplibre-gl`, `maplibre-gl-js` | Not required |
| Google Maps JavaScript API | `google`, `gmap`, `google-maps` | Required |

## Factory usage

```python
from mapwidgets import MapViewer

maplibre_viewer = MapViewer(backend="maplibre")
google_viewer = MapViewer(api_key="...", backend="google")
```

## Concrete classes

You can also instantiate the concrete classes directly:

```python
from mapwidgets import GoogleMapViewer, MapLibreViewer

maplibre_viewer = MapLibreViewer()
google_viewer = GoogleMapViewer(api_key="...")
```

MapLibre-specific methods include `set_projection`, `set_pitch`,
`set_bearing`, and `add_terrain`. Google-specific methods include `set_tilt`
and `set_heading`.

## Backend-neutral APIs

These methods are available through both viewer classes:

- `set_center(lat, lng)`
- `set_zoom(zoom)`
- `fit_bounds(bounds, padding=32, max_zoom=None)`
- `add_marker(marker, center_to=False)`
- `add_polyline(polyline, center_to=False)`
- `add_polygon(polygon, center_to=False)`
- `add_layer(layer, zoom_to=False, max_zoom=None, zoom_padding=32)`
- `zoom_to_layer(layer, padding=32, max_zoom=None)`
- `run_script(script, callback=None)`
