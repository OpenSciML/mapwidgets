from typing import Any

from .layers import RasterLayer, VectorLayer
from .map_elements import (
    Circle,
    Marker,
    Point,
    Polygon,
    Polyline,
    Rectangle,
    RectangleBounds,
)

__all__ = [
    "Circle",
    "BaseMapViewer",
    "GoogleMapViewer",
    "MapViewer",
    "MapLibreViewer",
    "Marker",
    "Point",
    "Polygon",
    "Polyline",
    "RasterLayer",
    "Rectangle",
    "RectangleBounds",
    "VectorLayer",
    "generate_geotiff_tiles",
    "optimize_geotiff_for_tiling",
    "prepare_geotiff_tiles",
]


def __getattr__(name: str) -> Any:
    """Lazily import optional modules so core schemas stay lightweight."""
    if name in {"BaseMapViewer", "GoogleMapViewer", "MapLibreViewer", "MapViewer"}:
        from .map_viewer import (
            BaseMapViewer,
            GoogleMapViewer,
            MapLibreViewer,
            MapViewer,
        )

        return {
            "BaseMapViewer": BaseMapViewer,
            "GoogleMapViewer": GoogleMapViewer,
            "MapLibreViewer": MapLibreViewer,
            "MapViewer": MapViewer,
        }[name]
    if name in {
        "generate_geotiff_tiles",
        "optimize_geotiff_for_tiling",
        "prepare_geotiff_tiles",
    }:
        from .raster_tiles import (
            generate_geotiff_tiles,
            optimize_geotiff_for_tiling,
            prepare_geotiff_tiles,
        )

        return {
            "generate_geotiff_tiles": generate_geotiff_tiles,
            "optimize_geotiff_for_tiling": optimize_geotiff_for_tiling,
            "prepare_geotiff_tiles": prepare_geotiff_tiles,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
