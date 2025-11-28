"""High-level entrypoint for routing that wires graph setup and UCS planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from .logger import Logger, LoggingMode
from .server.graph.stitch import stitch_path
from .server.search.ucs import plan as ucs_plan
from .setup import setup_graph

if TYPE_CHECKING:
    from .snap import Coordinate


def plan(
    start: Coordinate,
    destinations: Sequence[Coordinate],
    logging_mode: LoggingMode | str = LoggingMode.NONE,
) -> list[Coordinate]:
    """Build a LineString route starting at `start` and visiting destinations.

    All coordinates use `(lon, lat)` ordering.

    Parameters
    ----------
    start:
        Starting `(lon, lat)` coordinate.
    destinations:
        Sequence of `(lon, lat)` coordinates to visit.
    logging_mode:
        Controls log verbosity for the planning pipeline. Accepts
        `LoggingMode` values or their lowercase string names.

    """
    mode = LoggingMode.from_value(logging_mode)
    logger = Logger(mode)

    with logger.phase("graph.setup"):
        graph = setup_graph()
    logger.graph_stats(graph)

    node_path = ucs_plan(graph, start, destinations, logger=logger)
    return stitch_path(graph, node_path)
