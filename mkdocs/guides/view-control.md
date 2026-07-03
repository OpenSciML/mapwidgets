# View Control

Viewer methods return `self`, so map setup can be chained.

## Center and zoom

```python
viewer.set_center(32.2207, -98.2023).set_zoom(15)
```

## Fit bounds

```python
viewer.fit_bounds(
    {"west": -98.204, "south": 32.219, "east": -98.200, "north": 32.223},
    padding=48,
    max_zoom=18,
)
```

Bounds must use longitude/latitude coordinates:

- `west` and `east` are longitude values from -180 to 180.
- `south` and `north` are latitude values from -90 to 90.

## Current location

`center_on_current_location()` centers the map using an IP-based location lookup
from Python:

```python
viewer.center_on_current_location(zoom=14, add_marker=True)
```

This avoids macOS application bundle permission requirements for Qt location
services, but IP location is approximate and may be wrong by city or network
region. For field-grade accuracy, pass coordinates from GPS hardware or another
trusted location source to `set_center()`.

## Terrain

Terrain is currently a MapLibre feature:

```python
from mapwidgets import MapLibreViewer

viewer = (
    MapLibreViewer()
    .set_projection("mercator")
    .add_terrain(
        url="https://example.com/terrain/tiles.json",
        encoding="terrarium",
        exaggeration=1.5,
    )
)
```

Use a terrain-raster source compatible with MapLibre, such as Terrarium or
Mapbox-style RGB elevation tiles. Globe projection and terrain have limitations
in MapLibre, so use `mercator` when validating terrain rendering.
