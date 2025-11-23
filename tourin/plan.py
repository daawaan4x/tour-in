"""High-level entrypoint for routing that wires graph setup and UCS planning."""

from __future__ import annotations

from typing import Sequence

from .setup import setup_graph
from .ucs import Coordinate
from .ucs import plan as ucs_plan


def plan(
    start: Coordinate,
    destinations: Sequence[Coordinate],
) -> list[Coordinate]:
    """Build a LineString route starting at `start` and visiting destinations.

    All coordinates use `(lon, lat)` ordering.
    """
    graph = setup_graph()
    return ucs_plan(graph, start, destinations)
