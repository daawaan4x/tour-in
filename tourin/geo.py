"""Geospatial helpers shared across routing modules."""

from __future__ import annotations

import osmnx as ox

_GREAT_CIRCLE = getattr(ox.distance, "great_circle", None)
if _GREAT_CIRCLE is None:
    try:
        _GREAT_CIRCLE = ox.distance.great_circle_vec
    except AttributeError as exc:  # pragma: no cover - legacy fallback guard
        msg = "OSMnx distance helpers lack both `great_circle` and `great_circle_vec`."
        raise AttributeError(msg) from exc


def great_circle_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the great-circle distance between two lat/lon points in meters."""
    return float(_GREAT_CIRCLE(lat1, lon1, lat2, lon2))

