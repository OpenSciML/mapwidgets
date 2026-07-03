# Viewers

::: note
The viewer classes require the `pyside` extra because they wrap
`PySide6.QtWebEngineWidgets.QWebEngineView`.
:::

## `MapViewer(api_key=None, backend="maplibre", *args, **kwargs)`

Factory that returns a backend-specific viewer.

Supported backend names:

- `maplibre`, `maplibre-gl`, `maplibre-gl-js`
- `google`, `gmap`, `google-maps`

`api_key` is required for the Google Maps backend.

## `BaseMapViewer`

Shared viewer wrapper used by both concrete backends.

| Method | Purpose |
| --- | --- |
| `resize(*args)` | Resize the internal `QWebEngineView`. |
| `show()` / `hide()` | Show or hide the internal view. |
| `set_fixed_size(*args)` | Set a fixed view size. |
| `set_minimum_size(*args)` | Set a minimum view size. |
| `set_maximum_size(*args)` | Set a maximum view size. |
| `wait_for_map_ready()` | Block until the frontend map reports ready. |
| `run_script(script, callback=None)` | Run JavaScript after the map is ready. |
| `set_zoom(zoom)` | Set the map zoom. |
| `set_center(lat, lng)` | Set the map center. |
| `center_on_current_location(zoom=None, add_marker=False)` | Use an approximate IP-based location lookup. |
| `fit_bounds(bounds, padding=32, max_zoom=None)` | Fit the viewport to longitude/latitude bounds. |
| `add_marker(marker, center_to=False)` | Add a marker element. |
| `add_polyline(polyline, center_to=False)` | Add a polyline element. |
| `add_polygon(polygon, center_to=False)` | Add a polygon element. |
| `add_tile_overlay(tile_layer)` | Add a tile overlay config or layer object. |
| `add_layer(layer, zoom_to=False, max_zoom=None, zoom_padding=32)` | Add a backend-neutral layer. |
| `zoom_to_layer(layer, padding=32, max_zoom=None)` | Fit the viewport to a layer's bounds. |

## `MapLibreViewer`

Concrete MapLibre GL JS viewer.

Additional methods:

- `set_projection(projection)`
- `set_pitch(pitch)`
- `set_bearing(bearing)`
- `add_terrain(tiles=None, url=None, name="terrain", encoding="terrarium", exaggeration=1.0, tile_size=256, max_zoom=15, show_hillshade=True, attribution=None)`

## `GoogleMapViewer`

Concrete Google Maps JavaScript API viewer.

Additional methods:

- `set_tilt(tilt)`
- `set_heading(heading)`
