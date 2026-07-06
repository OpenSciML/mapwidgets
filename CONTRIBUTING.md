# Contributing

Thank you for helping improve mapwidgets. Keep changes focused, tested, and
consistent with the existing backend-neutral API.

## Development Setup

```bash
uv sync --group dev --group docs
make check
```

Install optional extras when manually testing GUI or geospatial workflows:

```bash
uv sync --extra pyside --extra geospatial --group dev --group docs
```

## Pull Requests

- Keep MapLibre and Google Maps behavior aligned unless the change is
  intentionally backend-specific.
- Add or update tests for layer, tiling, or schema changes.
- Update README and MkDocs pages when public APIs or install steps change.
- Do not commit `.env` files, generated caches, local build outputs, or private
  map-service keys.

## Reporting Issues

Include your operating system, Python version, installed extras, backend
(`maplibre` or `google`), and a minimal code sample or traceback.
