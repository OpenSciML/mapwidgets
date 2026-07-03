# Map Elements

Basic map elements are backend-neutral Pydantic models. All fields are optional
at model construction time, which makes it possible to build partial element
configs when a backend only needs a subset of properties.

## Marker

```python
from mapwidgets import Marker

viewer.add_marker(
    Marker(
        position={"lat": 32.2207, "lng": -98.2023},
        title="Sample",
    )
)
```

## Polyline

```python
from mapwidgets import Polyline

viewer.add_polyline(
    Polyline(
        path=[
            {"lat": 32.2207, "lng": -98.2023},
            {"lat": 32.2212, "lng": -98.2015},
        ],
        strokeColor="#0f766e",
        strokeWeight=3,
    )
)
```

## Polygon

```python
from mapwidgets import Polygon

viewer.add_polygon(
    Polygon(
        paths=[
            {"lat": 32.2207, "lng": -98.2023},
            {"lat": 32.2212, "lng": -98.2020},
            {"lat": 32.2209, "lng": -98.2015},
        ],
        fillColor="#2563eb",
        fillOpacity=0.35,
    )
)
```

## Coordinate convention

Element coordinates use dictionaries with `lat` and `lng` keys:

```python
{"lat": 32.2207, "lng": -98.2023}
```

Layer bounds use `north`, `south`, `east`, and `west` keys.
