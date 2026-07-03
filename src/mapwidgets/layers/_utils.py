"""Internal helpers for map layer models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def file_base_url(path: Path) -> str:
    """Return a browser-usable base URL for a static XYZ tile directory."""
    return path.expanduser().resolve().as_uri()


def geojson_bounds(data: dict[str, Any]) -> dict[str, float] | None:
    """Return north/south/east/west bounds for a GeoJSON object."""
    coordinates = list(_iter_geojson_coordinates(data))
    if not coordinates:
        return None

    lng_values = [coordinate[0] for coordinate in coordinates]
    lat_values = [coordinate[1] for coordinate in coordinates]
    return {
        "north": max(lat_values),
        "south": min(lat_values),
        "east": max(lng_values),
        "west": min(lng_values),
    }


def validate_lnglat_bounds(bounds: dict[str, float] | None) -> dict[str, float] | None:
    """Validate bounds are in longitude/latitude coordinate ranges."""
    if bounds is None:
        return None

    required_keys = {"north", "south", "east", "west"}
    missing_keys = required_keys - bounds.keys()
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"Layer bounds are missing required keys: {missing}.")

    north = bounds["north"]
    south = bounds["south"]
    east = bounds["east"]
    west = bounds["west"]
    if not -90 <= south <= 90 or not -90 <= north <= 90:
        raise ValueError(
            "Layer bounds must use latitude/longitude coordinates. "
            f"Got south={south}, north={north}."
        )
    if not -180 <= west <= 180 or not -180 <= east <= 180:
        raise ValueError(
            "Layer bounds must use latitude/longitude coordinates. "
            f"Got west={west}, east={east}."
        )
    if south > north:
        raise ValueError(f"Layer bounds are invalid: south={south} > north={north}.")
    return bounds


def read_geotiff_bounds(path: Path) -> dict[str, float] | None:
    """Read GeoTIFF bounds in EPSG:4326 when rasterio is available."""
    try:
        import rasterio
        from rasterio.warp import transform_bounds
    except ImportError:
        return None

    with rasterio.open(path) as dataset:
        bounds = dataset.bounds
        if dataset.crs:
            west, south, east, north = transform_bounds(
                dataset.crs,
                "EPSG:4326",
                bounds.left,
                bounds.bottom,
                bounds.right,
                bounds.top,
                densify_pts=21,
            )
        else:
            west, south, east, north = (
                bounds.left,
                bounds.bottom,
                bounds.right,
                bounds.top,
            )

    return validate_lnglat_bounds(
        {"north": north, "south": south, "east": east, "west": west}
    )


def read_vector_file(path: Path) -> dict[str, Any]:
    """Read a vector dataset as a GeoJSON mapping."""
    suffix = path.suffix.lower()
    if suffix in {".geojson", ".json"}:
        return json.loads(path.read_text())

    try:
        import geopandas as gpd
    except ImportError:
        gpd = None

    if gpd is not None:
        data_frame = gpd.read_file(path)
        if data_frame.crs is not None:
            data_frame = data_frame.to_crs("EPSG:4326")
        geojson = json.loads(data_frame.to_json())
        validate_lnglat_bounds(geojson_bounds(geojson))
        return geojson

    try:
        import fiona
        from shapely.geometry import mapping, shape
        from shapely.ops import transform
    except ImportError as exc:
        raise ImportError(
            "VectorLayer.from_shapefile() requires geopandas, or fiona and "
            "shapely, to read Shapefiles. Install one of those optional "
            "geospatial stacks or pass a GeoJSON file instead."
        ) from exc

    features = []
    with fiona.open(path) as source:
        transformer = _feature_transformer(source.crs)
        for feature in source:
            geometry = shape(feature["geometry"])
            if transformer is not None:
                geometry = transform(transformer, geometry)
            features.append(
                {
                    "type": "Feature",
                    "geometry": mapping(geometry),
                    "properties": dict(feature["properties"]),
                }
            )
    geojson = {"type": "FeatureCollection", "features": features}
    validate_lnglat_bounds(geojson_bounds(geojson))
    return geojson


def _feature_transformer(crs: Any) -> Any:
    """Return a coordinate transformer from source CRS to EPSG:4326."""
    if not crs:
        return None

    try:
        from pyproj import CRS, Transformer
    except ImportError:
        return None

    source_crs = CRS.from_user_input(crs)
    if source_crs.equals(CRS.from_epsg(4326)):
        return None

    transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    return transformer.transform


def _iter_geojson_coordinates(data: dict[str, Any]) -> Any:
    """Yield coordinate pairs from GeoJSON-like mappings."""
    geojson_type = data.get("type")
    if geojson_type == "FeatureCollection":
        for feature in data.get("features", []):
            yield from _iter_geojson_coordinates(feature)
    elif geojson_type == "Feature":
        geometry = data.get("geometry")
        if geometry:
            yield from _iter_geojson_coordinates(geometry)
    elif geojson_type == "GeometryCollection":
        for geometry in data.get("geometries", []):
            yield from _iter_geojson_coordinates(geometry)
    elif "coordinates" in data:
        yield from _iter_coordinates(data["coordinates"])


def _iter_coordinates(coordinates: Any) -> Any:
    """Yield coordinate pairs from nested GeoJSON coordinate arrays."""
    if (
        isinstance(coordinates, list)
        and len(coordinates) >= 2
        and isinstance(coordinates[0], int | float)
        and isinstance(coordinates[1], int | float)
    ):
        yield coordinates
        return

    if isinstance(coordinates, list):
        for item in coordinates:
            yield from _iter_coordinates(item)
