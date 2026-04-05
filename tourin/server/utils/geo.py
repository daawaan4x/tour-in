"""Geospatial helpers shared across routing modules."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

import osmnx as ox

GreatCircleFn = Callable[[float, float, float, float], float]

_great_circle: GreatCircleFn | None = getattr(ox.distance, "great_circle", None)
if _great_circle is None:
    legacy_fn = getattr(ox.distance, "great_circle_vec", None)
    if legacy_fn is None:
        msg = "OSMnx distance helpers lack both `great_circle` and `great_circle_vec`."
        raise AttributeError(msg)
    _great_circle = cast(GreatCircleFn, legacy_fn)
if _great_circle is None:  # pragma: no cover - defensive guard for type-checkers
    msg = "OSMnx distance helpers are unavailable."
    raise AttributeError(msg)

_GREAT_CIRCLE: GreatCircleFn = _great_circle


Coordinate = tuple[float, float]  # (lon, lat)


def great_circle_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Return the great-circle distance between two lat/lon points in meters."""
    return float(_GREAT_CIRCLE(lat1, lon1, lat2, lon2))
