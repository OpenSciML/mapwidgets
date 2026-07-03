"""Vector map layer models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ._utils import geojson_bounds, read_vector_file, validate_lnglat_bounds


@dataclass
class VectorLayer:
    """GeoJSON-backed vector layer."""

    id: str
    data: dict[str, Any]
    geometry: Literal["auto", "point", "line", "polygon"] = "auto"
    name: str | None = None
    fill_color: str = "#1f78ff"
    fill_opacity: float = 0.35
    stroke_color: str = "#1f78ff"
    stroke_opacity: float = 1.0
    stroke_width: int = 2
    circle_color: str = "#1f78ff"
    circle_radius: int = 5
    bounds: dict[str, float] | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_shapefile(
        cls,
        path: str | Path,
        *,
        id: str | None = None,
        name: str | None = None,
        geometry: Literal["auto", "point", "line", "polygon"] = "auto",
        fill_color: str = "#1f78ff",
        fill_opacity: float = 0.35,
        stroke_color: str = "#1f78ff",
        stroke_opacity: float = 1.0,
        stroke_width: int = 2,
        circle_color: str = "#1f78ff",
        circle_radius: int = 5,
        bounds: dict[str, float] | None = None,
    ) -> VectorLayer:
        """Read a Shapefile into a GeoJSON vector layer.

        Parameters
        ----------
        path
            Path to a ``.shp`` file.
        id
            Layer id used by the frontend.
        name
            Human-readable layer name.
        geometry
            Preferred renderer. ``"auto"`` chooses from feature geometry.
        fill_color
            Polygon fill color.
        fill_opacity
            Polygon fill opacity.
        stroke_color
            Line and polygon stroke color.
        stroke_opacity
            Line and polygon stroke opacity.
        stroke_width
            Line and polygon stroke width.
        circle_color
            Point circle color.
        circle_radius
            Point circle radius in pixels.
        bounds
            Optional layer bounds as ``north``, ``south``, ``east``, and
            ``west``. If omitted, bounds are computed from GeoJSON geometry.
        """
        shapefile_path = Path(path)
        layer_id = id or shapefile_path.stem
        data = read_vector_file(shapefile_path)
        return cls(
            id=layer_id,
            name=name or layer_id,
            data=data,
            geometry=geometry,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            stroke_color=stroke_color,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
            circle_color=circle_color,
            circle_radius=circle_radius,
            bounds=validate_lnglat_bounds(bounds) or geojson_bounds(data),
        )

    def map_config(self) -> dict[str, Any]:
        """Return a backend-neutral vector layer config."""
        return {
            "type": "vector",
            "id": self.id,
            "name": self.name,
            "data": self.data,
            "geometry": self.geometry,
            "bounds": validate_lnglat_bounds(self.bounds or geojson_bounds(self.data)),
            "paint": {
                "fillColor": self.fill_color,
                "fillOpacity": self.fill_opacity,
                "strokeColor": self.stroke_color,
                "strokeOpacity": self.stroke_opacity,
                "strokeWidth": self.stroke_width,
                "circleColor": self.circle_color,
                "circleRadius": self.circle_radius,
            },
            "properties": self.properties,
        }

    def maplibre_config(self) -> dict[str, Any]:
        """Return a MapLibre GeoJSON layer config."""
        return self.map_config()

    def google_maps_config(self) -> dict[str, Any]:
        """Return a Google Maps Data layer config."""
        return self.map_config()
