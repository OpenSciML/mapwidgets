"""Command-line helpers for mapwidgets."""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    """Run a small desktop map demo.

    Parameters
    ----------
    argv
        Optional command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit status code.
    """
    parser = argparse.ArgumentParser(description="Open a mapwidgets demo map.")
    parser.add_argument(
        "--backend",
        choices=("maplibre", "google"),
        default=os.getenv("MAPWIDGETS_BACKEND", "maplibre"),
        help="Map backend to use.",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=32.2207,
        help="Initial map center latitude.",
    )
    parser.add_argument(
        "--lng",
        type=float,
        default=-98.2023,
        help="Initial map center longitude.",
    )
    parser.add_argument("--zoom", type=float, default=15, help="Initial zoom level.")
    args = parser.parse_args(argv)

    load_dotenv()

    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QApplication

    from mapwidgets import MapViewer, Marker

    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if args.backend == "google" and not api_key:
        parser.error("GOOGLE_MAPS_API_KEY is required when --backend=google.")

    app = QApplication.instance() or QApplication(sys.argv[:1])
    viewer = (
        MapViewer(api_key=api_key, backend=args.backend)
        .resize(QSize(900, 600))
        .set_center(args.lat, args.lng)
        .set_zoom(args.zoom)
        .add_marker(
            Marker(
                position={"lat": args.lat, "lng": args.lng},
                title="Map center",
            )
        )
    )
    viewer.show().wait_for_map_ready()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
