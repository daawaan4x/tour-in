"""High-level entrypoint for routing that wires graph setup and UCS planning."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from tourin.server.graph.load import load_graph
from tourin.server.graph.snap import snap_coords

from .graph.stitch import stitch_path
from .search.ucs import plan as ucs_plan

if TYPE_CHECKING:
    from tourin.server.utils.geo import Coordinate


def plan(
    start: Coordinate,
    destinations: Sequence[Coordinate],
) -> list[Coordinate]:
    """Build a LineString route starting at `start` and visiting destinations.

    All coordinates use `(lon, lat)` ordering.

    Parameters
    ----------
    start:
        Starting `(lon, lat)` coordinate.
    destinations:
        Sequence of `(lon, lat)` coordinates to visit.

    """
    graph = load_graph()

    snapped_nodes = snap_coords(graph, [start, *destinations])
    start_node = snapped_nodes[0].node_id
    target_nodes = [node.node_id for node in snapped_nodes[1:]]

    node_path = ucs_plan(graph, start_node, target_nodes)
    return stitch_path(graph, node_path)
