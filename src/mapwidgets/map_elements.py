"""Shared Pydantic schemas for map rendering backends."""

from typing import Any, Optional, Type

from pydantic import BaseModel, create_model


def partial_model(model: Type[BaseModel]) -> Type[BaseModel]:
    """Return a Pydantic model with all fields made optional."""
    fields = {}
    for field_name, field_type in model.__annotations__.items():
        fields[field_name] = (Optional[field_type], None)
    return create_model(
        f"Partial{model.__name__}",
        __base__=model,
        __module__=model.__module__,
        **fields,
    )


@partial_model
class Point(BaseModel):
    """Geographic latitude/longitude coordinate used by map elements."""

    lat: float
    lng: float


@partial_model
class Marker(BaseModel):
    """Point marker rendered on a map."""

    position: Point
    title: str
    draggable: bool
    properties: dict[str, Any]


@partial_model
class Polyline(BaseModel):
    """Ordered path rendered as a map polyline."""

    path: list[Point]
    geodesic: bool
    strokeColor: str
    strokeOpacity: float
    strokeWeight: int
    properties: dict[str, Any]


@partial_model
class Polygon(BaseModel):
    """Closed polygon rendered by map backends."""

    paths: list[Point]
    strokeColor: str
    strokeOpacity: float
    strokeWeight: int
    fillColor: str
    fillOpacity: float
    properties: dict[str, Any]


@partial_model
class Circle(BaseModel):
    """Circle overlay rendered from a center point and radius."""

    center: Point
    radius: float
    strokeColor: str
    strokeOpacity: float
    strokeWeight: int
    fillColor: str
    fillOpacity: float
    properties: dict[str, Any]


@partial_model
class RectangleBounds(BaseModel):
    """North/south/east/west rectangle bounds."""

    north: float
    south: float
    east: float
    west: float


@partial_model
class Rectangle(BaseModel):
    """Rectangle overlay rendered from geographic bounds."""

    bounds: RectangleBounds
    strokeColor: str
    strokeOpacity: float
    strokeWeight: int
    fillColor: str
    fillOpacity: float
    properties: dict[str, Any]
