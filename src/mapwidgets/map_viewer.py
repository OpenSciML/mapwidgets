import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Self
from urllib.error import URLError
from urllib.request import Request, urlopen

try:
    from PySide6.QtCore import QEventLoop, QObject, QUrl, Signal, Slot
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineCore import QWebEngineSettings
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError as exc:
    raise ImportError(
        "PySide6 is required to use MapViewer. Install it with "
        "`pip install mapwidgets[pyside]`."
    ) from exc

from .map_elements import Marker, Point, Polygon, Polyline


def _validate_lnglat_bounds(bounds: dict[str, float]) -> dict[str, float]:
    """Validate bounds are in longitude/latitude coordinate ranges."""
    north = bounds.get("north")
    south = bounds.get("south")
    east = bounds.get("east")
    west = bounds.get("west")
    if north is None or south is None or east is None or west is None:
        raise ValueError("Bounds must include north, south, east, and west.")
    if not -90 <= south <= 90 or not -90 <= north <= 90:
        raise ValueError(
            "Bounds must use latitude/longitude coordinates. "
            f"Got south={south}, north={north}."
        )
    if not -180 <= west <= 180 or not -180 <= east <= 180:
        raise ValueError(
            "Bounds must use latitude/longitude coordinates. "
            f"Got west={west}, east={east}."
        )
    return bounds


GOOGLE_BACKEND_ALIASES = {"google", "gmap", "google-maps"}
MAPLIBRE_BACKEND_ALIASES = {"maplibre", "maplibre-gl", "maplibre-gl-js"}
SUPPORTED_BACKENDS = GOOGLE_BACKEND_ALIASES | MAPLIBRE_BACKEND_ALIASES


class MapViewerFrontendEventHandler(QObject):
    """Handles map frontend events."""

    mapClicked = Signal(float, float)
    elementClicked = Signal(str, object)
    mapReady = Signal()

    def __init__(self, map_viewer: Any | None = None, api_key: str = "") -> None:
        """Create a frontend event bridge.

        Parameters
        ----------
        map_viewer
            PySide web view that receives frontend JavaScript calls.
        api_key
            Optional map service API key returned to the frontend.
        """
        super().__init__()
        self.map_viewer = map_viewer
        self.api_key = api_key

    @Slot()
    def getApiKey(self) -> None:
        """Send the configured map service API key to the frontend."""
        if not self.map_viewer:
            return
        self.map_viewer.page().runJavaScript(
            f"loadGoogleMaps({json.dumps(self.api_key)});"
        )

    @Slot()
    def on_map_ready(self) -> None:
        """Emit the backend map-ready signal after frontend initialization."""
        print("Map initialized and ready.")
        self.mapReady.emit()

    @Slot(str)
    def log(self, msg: str) -> None:
        """Print a frontend log message routed through the web channel."""
        print(f"JS Log: {msg}")

    @Slot(str, str)
    def on_element_click(self, element_type: str, payload_json: str) -> None:
        """Emit an element-click signal from a frontend payload."""
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            payload = {"raw": payload_json}
        self.elementClicked.emit(element_type, payload)


class BaseMapViewer:
    """Shared PySide QWebEngineView wrapper for map backends."""

    backend: str
    html_file: str
    js_prefix: str

    def __init__(self, api_key: str | None = None, *args: Any, **kwargs: Any) -> None:
        """Create a web view for this backend.

        Parameters
        ----------
        api_key
            Optional service API key made available to the frontend.
        *args
            Extra positional arguments forwarded to ``QWebEngineView``.
        **kwargs
            Extra keyword arguments forwarded to ``QWebEngineView``.
        """
        self.api_key = api_key or ""
        self._view = QWebEngineView(*args, **kwargs)
        self._channel = QWebChannel()
        self._page = self._view.page()
        self._page.setWebChannel(self._channel)
        self._handler = MapViewerFrontendEventHandler(self, self.api_key)
        self._map_ready = False
        self._pending_scripts: list[tuple[str, Callable[[Any], None] | None]] = []
        self._element_click_callbacks: list[Callable[[str, dict[str, Any]], None]] = []
        self._handler.mapReady.connect(self._mark_map_ready)
        self._handler.elementClicked.connect(self._dispatch_element_click)
        self._channel.registerObject("qtMapViewer", self._handler)

        settings = self._page.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        file_path = Path(__file__).parent / self.html_file
        self._view.load(QUrl.fromLocalFile(str(file_path)))

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the internal QWebEngineView."""
        if hasattr(self._view, name):
            return getattr(self._view, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def _backend_function(self, function_name: str) -> str:
        """Return the JavaScript function name for this backend."""
        return f"{self.js_prefix}_{function_name}"

    def _mark_map_ready(self) -> None:
        """Mark the frontend ready and flush queued JavaScript commands."""
        self._map_ready = True
        pending_scripts = self._pending_scripts
        self._pending_scripts = []
        for script, callback in pending_scripts:
            if callback:
                self._page.runJavaScript(script, callback)
            else:
                self._page.runJavaScript(script)

    def resize(self, *args: Any) -> Self:
        """Resize the view and return this viewer for method chaining."""
        self._view.resize(*args)
        return self

    def show(self) -> Self:
        """Show the view and return this viewer for method chaining."""
        self._view.show()
        return self

    def hide(self) -> Self:
        """Hide the view and return this viewer for method chaining."""
        self._view.hide()
        return self

    def set_fixed_size(self, *args: Any) -> Self:
        """Set a fixed view size and return this viewer for method chaining."""
        self._view.setFixedSize(*args)
        return self

    def setFixedSize(self, *args: Any) -> Self:
        """Set a fixed view size and return this viewer for method chaining."""
        return self.set_fixed_size(*args)

    def set_minimum_size(self, *args: Any) -> Self:
        """Set a minimum view size and return this viewer for method chaining."""
        self._view.setMinimumSize(*args)
        return self

    def setMinimumSize(self, *args: Any) -> Self:
        """Set a minimum view size and return this viewer for method chaining."""
        return self.set_minimum_size(*args)

    def set_maximum_size(self, *args: Any) -> Self:
        """Set a maximum view size and return this viewer for method chaining."""
        self._view.setMaximumSize(*args)
        return self

    def setMaximumSize(self, *args: Any) -> Self:
        """Set a maximum view size and return this viewer for method chaining."""
        return self.set_maximum_size(*args)

    def wait_for_map_ready(self) -> Self:
        """Block until the JavaScript map reports ready, then return this viewer."""
        if self._map_ready:
            return self

        loop = QEventLoop()
        self._handler.mapReady.connect(loop.quit)
        print("Waiting for the map to be ready...")
        loop.exec()
        print("Map is now ready!")
        return self

    def run_script(
        self, script: str, callback: Callable[[Any], None] | None = None
    ) -> Self:
        """Run JavaScript in the embedded map page and return this viewer."""
        if not self._map_ready:
            self._pending_scripts.append((script, callback))
            return self

        if callback:
            self._page.runJavaScript(script, callback)
        else:
            self._page.runJavaScript(script)
        return self

    def on_element_click(self, callback: Callable[[str, dict[str, Any]], None]) -> Self:
        """Register a callback for marker, polyline, and polygon clicks.

        Parameters
        ----------
        callback
            Callable receiving the element type and click payload. The payload
            contains ``properties`` with the custom application metadata and
            ``element`` with the original element configuration.
        """
        self._element_click_callbacks.append(callback)
        return self

    def _dispatch_element_click(self, element_type: str, payload: object) -> None:
        """Dispatch a frontend element-click payload to registered callbacks."""
        payload_dict = payload if isinstance(payload, dict) else {"value": payload}
        for callback in self._element_click_callbacks:
            callback(element_type, payload_dict)

    def set_zoom(self, zoom: int | float) -> Self:
        """Set the active map zoom level and return this viewer."""
        self.run_script(f"{self._backend_function('setZoom')}({zoom})")
        return self

    def set_center(self, lat: float, lng: float) -> Self:
        """Set the active map center and return this viewer."""
        self.run_script(f"{self._backend_function('setCenter')}({lat}, {lng})")
        return self

    def center_on_current_location(
        self, zoom: int | float | None = None, add_marker: bool = False
    ) -> Self:
        """Center the map on the current network-derived location.

        Parameters
        ----------
        zoom
            Optional zoom level to apply after the location is found.
        add_marker
            Whether to add a marker at the detected location.
        """
        location = self._current_location()
        if location is None:
            return self

        lat, lng = location
        self.set_center(lat, lng)
        if zoom is not None:
            self.set_zoom(zoom)
        if add_marker:
            self.add_marker(
                Marker(  # type: ignore[call-arg]
                    position=Point(lat=lat, lng=lng),
                    title="Current location",
                )
            )
        return self

    def _current_location(self) -> tuple[float, float] | None:
        """Return an approximate current location from an IP lookup."""
        request = Request(
            "https://ipapi.co/json/",
            headers={"User-Agent": "mapwidgets/0.1"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"Location lookup failed: {exc}")
            return None

        lat = payload.get("latitude")
        lng = payload.get("longitude")
        if not isinstance(lat, int | float) or not isinstance(lng, int | float):
            print("Location lookup failed: response did not include coordinates.")
            return None
        return float(lat), float(lng)

    def fit_bounds(
        self,
        bounds: dict[str, float],
        *,
        padding: int = 32,
        max_zoom: int | float | None = None,
    ) -> Self:
        """Fit the map viewport to geographic bounds and return this viewer."""
        bounds = _validate_lnglat_bounds(bounds)
        bounds_object = json.dumps(bounds)
        options = {"padding": padding, "maxZoom": max_zoom}
        options_object = json.dumps(options)
        self.run_script(
            f"{self._backend_function('fitBounds')}({bounds_object}, {options_object});"
        )
        return self

    def add_marker(self, marker: Marker, center_to: bool = False) -> Self:
        """Add a marker to the embedded map and return this viewer."""
        center_to_js = "true" if center_to else "false"
        json_object = marker.model_dump_json(exclude_none=True)
        self.run_script(
            f"{self._backend_function('addMarker')}({json_object}, {center_to_js});"
        )
        return self

    def add_polyline(self, polyline: Polyline, center_to: bool = False) -> Self:
        """Add a polyline to the embedded map and return this viewer."""
        center_to_js = "true" if center_to else "false"
        json_object = polyline.model_dump_json(exclude_none=True)
        self.run_script(
            f"{self._backend_function('addPolyline')}({json_object}, {center_to_js});"
        )
        return self

    def add_polygon(self, polygon: Polygon, center_to: bool = False) -> Self:
        """Add a polygon to the embedded map and return this viewer."""
        center_to_js = "true" if center_to else "false"
        json_object = polygon.model_dump_json(exclude_none=True)
        self.run_script(
            f"{self._backend_function('addPolygon')}({json_object}, {center_to_js});"
        )
        return self

    def add_tile_overlay(self, tile_layer: Any) -> Self:
        """Add a generated raster tile overlay to the active map backend.

        Parameters
        ----------
        tile_layer
            Mapping with tile configuration, or an object exposing
            ``map_config()`` or ``google_maps_config()``. The config must
            include ``baseUrl`` and can include ``minZoom``, ``maxZoom``,
            ``tileSize``, ``name``, ``opacity``, and ``cacheKey``.
        """
        if isinstance(tile_layer, dict):
            tile_config = tile_layer
        elif hasattr(tile_layer, "map_config"):
            tile_config = tile_layer.map_config()
        else:
            tile_config = tile_layer.google_maps_config()
        json_object = json.dumps(tile_config)
        self.run_script(f"{self._backend_function('addTileOverlay')}({json_object});")
        return self

    def _layer_config(self, layer: Any) -> dict[str, Any]:
        """Return a layer config for the active backend."""
        if isinstance(layer, dict):
            return layer

        backend_config_name = (
            "google_maps_config" if self.backend == "google" else "maplibre_config"
        )
        if hasattr(layer, backend_config_name):
            return getattr(layer, backend_config_name)()
        if hasattr(layer, "map_config"):
            return layer.map_config()
        raise TypeError(
            "Layer objects must expose map_config(), maplibre_config(), "
            "google_maps_config(), or be a layer configuration dict."
        )

    def add_layer(
        self,
        layer: Any,
        zoom_to: bool = False,
        *,
        max_zoom: int | float | None = None,
        zoom_padding: int = 32,
    ) -> Self:
        """Add a backend-neutral map layer and return this viewer.

        Parameters
        ----------
        layer
            Layer object exposing ``map_config()``, ``maplibre_config()``, or
            ``google_maps_config()`` depending on the active backend.
        zoom_to
            Whether to fit the map viewport to this layer after adding it.
        max_zoom
            Maximum zoom level to use when ``zoom_to`` is enabled.
        zoom_padding
            Padding in pixels to use when ``zoom_to`` is enabled.
        """
        layer_config = self._layer_config(layer)
        json_object = json.dumps(layer_config)
        self.run_script(f"{self._backend_function('addLayer')}({json_object});")
        if zoom_to:
            self.zoom_to_layer(
                layer_config,
                max_zoom=max_zoom,
                padding=zoom_padding,
            )
        return self

    def zoom_to_layer(
        self,
        layer: Any,
        *,
        padding: int = 32,
        max_zoom: int | float | None = None,
    ) -> Self:
        """Fit the viewport to a layer's bounds and return this viewer.

        Parameters
        ----------
        layer
            Layer object or config with ``bounds`` containing ``north``,
            ``south``, ``east``, and ``west``.
        padding
            Fit-bounds padding in pixels.
        max_zoom
            Maximum zoom level after fitting bounds.
        """
        layer_config = self._layer_config(layer)
        bounds = layer_config.get("bounds")
        if not bounds:
            layer_id = layer_config.get("id", "layer")
            raise ValueError(
                f"Cannot zoom to {layer_id!r}: layer bounds are not available. "
                "Pass bounds=... when creating the layer, or install rasterio "
                "for GeoTIFF bounds."
            )
        self.fit_bounds(bounds, padding=padding, max_zoom=max_zoom)
        return self


class GoogleMapViewer(BaseMapViewer):
    """Google Maps JavaScript API viewer."""

    backend = "google"
    html_file = "gmap_index.html"
    js_prefix = "gmap"

    def __init__(self, api_key: str | None = None, *args: Any, **kwargs: Any) -> None:
        """Create a Google Maps viewer.

        Parameters
        ----------
        api_key
            Google Maps JavaScript API key.
        *args
            Extra positional arguments forwarded to ``QWebEngineView``.
        **kwargs
            Extra keyword arguments forwarded to ``QWebEngineView``.
        """
        if not api_key:
            raise ValueError("Google Maps backend requires an API key.")
        super().__init__(api_key=api_key, *args, **kwargs)  # type: ignore[misc]

    def set_tilt(self, tilt: float) -> Self:
        """Set Google Maps camera tilt and return this viewer."""
        self.run_script(f"{self._backend_function('setTilt')}({tilt})")
        return self

    def set_heading(self, heading: float) -> Self:
        """Set Google Maps camera heading and return this viewer."""
        self.run_script(f"{self._backend_function('setHeading')}({heading})")
        return self


class MapLibreViewer(BaseMapViewer):
    """MapLibre GL JS viewer."""

    backend = "maplibre"
    html_file = "maplibre_index.html"
    js_prefix = "maplibre"

    def set_projection(self, projection: str) -> Self:
        """Set the MapLibre projection, such as ``"mercator"`` or ``"globe"``."""
        self.run_script(
            f"{self._backend_function('setProjection')}({json.dumps(projection)});"
        )
        return self

    def set_pitch(self, pitch: float) -> Self:
        """Set the MapLibre camera pitch and return this viewer."""
        self.run_script(f"{self._backend_function('setPitch')}({pitch});")
        return self

    def set_bearing(self, bearing: float) -> Self:
        """Set the MapLibre camera bearing and return this viewer."""
        self.run_script(f"{self._backend_function('setBearing')}({bearing});")
        return self

    def add_terrain(
        self,
        tiles: list[str] | None = None,
        *,
        url: str | None = None,
        name: str = "terrain",
        encoding: str = "terrarium",
        exaggeration: float = 1.0,
        tile_size: int = 256,
        max_zoom: int = 15,
        show_hillshade: bool = True,
        attribution: str | None = None,
    ) -> Self:
        """Add a MapLibre ``raster-dem`` terrain source and enable terrain.

        Parameters
        ----------
        tiles
            XYZ raster DEM tile URL templates. Use this or ``url``.
        url
            TileJSON URL for a raster DEM source. Use this or ``tiles``.
        name
            Source name used by MapLibre.
        encoding
            DEM tile encoding. MapLibre supports ``"terrarium"``, ``"mapbox"``,
            and ``"custom"``.
        exaggeration
            Terrain elevation exaggeration factor.
        tile_size
            DEM tile size in pixels.
        max_zoom
            Maximum zoom level available in the DEM tile set.
        show_hillshade
            Whether to add a hillshade layer so elevation is visibly shaded.
        attribution
            Optional terrain source attribution.
        """
        if not tiles and not url:
            raise ValueError("add_terrain() requires either 'tiles' or 'url'.")

        config = {
            "tiles": tiles,
            "url": url,
            "name": name,
            "encoding": encoding,
            "exaggeration": exaggeration,
            "tileSize": tile_size,
            "maxZoom": max_zoom,
            "showHillshade": show_hillshade,
            "attribution": attribution,
        }
        self.run_script(
            f"{self._backend_function('addTerrain')}({json.dumps(config)});"
        )
        return self


def MapViewer(
    api_key: str | None = None,
    backend: str = "maplibre",
    *args: Any,
    **kwargs: Any,
) -> BaseMapViewer:
    """Create a backend-specific map viewer.

    Parameters
    ----------
    api_key
        Optional backend API key. Required for Google Maps.
    backend
        Backend name. Supported values include ``"google"`` and ``"maplibre"``.
    *args
        Extra positional arguments forwarded to the backend viewer.
    **kwargs
        Extra keyword arguments forwarded to the backend viewer.
    """
    if "provider" in kwargs:
        if backend != "maplibre":
            raise TypeError("Use either 'backend' or legacy 'provider', not both.")
        backend = kwargs.pop("provider")

    backend_key = backend.lower()
    if backend_key in GOOGLE_BACKEND_ALIASES:
        return GoogleMapViewer(api_key=api_key, *args, **kwargs)  # type: ignore[misc]
    if backend_key in MAPLIBRE_BACKEND_ALIASES:
        return MapLibreViewer(api_key=api_key, *args, **kwargs)  # type: ignore[misc]

    supported_backends = ", ".join(sorted(SUPPORTED_BACKENDS))
    raise ValueError(
        f"Unsupported map backend {backend!r}. Supported backends: "
        f"{supported_backends}."
    )
