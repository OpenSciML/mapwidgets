# Elements

Element models are Pydantic models defined in `mapwidgets.map_elements`.

## `Point`

```python
Point(lat=32.2207, lng=-98.2023)
```

Fields:

- `lat: float`
- `lng: float`

## `Marker`

Fields:

- `position: Point`
- `title: str`
- `draggable: bool`

## `Polyline`

Fields:

- `path: list[Point]`
- `geodesic: bool`
- `strokeColor: str`
- `strokeOpacity: float`
- `strokeWeight: int`

## `Polygon`

Fields:

- `paths: list[Point]`
- `strokeColor: str`
- `strokeOpacity: float`
- `strokeWeight: int`
- `fillColor: str`
- `fillOpacity: float`

## `Circle`

Fields:

- `center: Point`
- `radius: float`
- `strokeColor: str`
- `strokeOpacity: float`
- `strokeWeight: int`
- `fillColor: str`
- `fillOpacity: float`

## `RectangleBounds`

Fields:

- `north: float`
- `south: float`
- `east: float`
- `west: float`

## `Rectangle`

Fields:

- `bounds: RectangleBounds`
- `strokeColor: str`
- `strokeOpacity: float`
- `strokeWeight: int`
- `fillColor: str`
- `fillOpacity: float`
