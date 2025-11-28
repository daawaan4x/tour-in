"""Helpers for expanding graph node paths into coordinate sequences."""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Hashable, Sequence

if TYPE_CHECKING:
    import networkx as nx

    from tourin.server.utils.geo import Coordinate


def stitch_path(
    graph: nx.MultiGraph,
    nodes: Sequence[Hashable],
) -> list[Coordinate]:
    """Expand a node path into full geometry-aware coordinates."""
    if not nodes:
        return []

    stitched: list[Coordinate] = [
        (graph.nodes[nodes[0]]["x"], graph.nodes[nodes[0]]["y"]),
    ]

    for u, v in pairwise(nodes):
        segment = edge_geometry_coords(graph, u, v)
        # Skip the first coordinate to avoid duplicates.
        stitched.extend(segment[1:])

    return stitched


def edge_geometry_coords(
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
) -> list[Coordinate]:
    """Return the geometry coordinates between adjacent nodes."""
    candidate = preferred_edge_attrs(graph, u, v)
    start = (graph.nodes[u]["x"], graph.nodes[u]["y"])
    end = (graph.nodes[v]["x"], graph.nodes[v]["y"])

    if candidate is None:
        return [start, end]

    coords = extract_geometry_coords(candidate.get("geometry"))
    if not coords:
        return [start, end]

    # Ensure polyline runs from node `u` to node `v` and touches their exact coordinates.  # noqa: E501
    if squared_distance(coords[0], start) > squared_distance(coords[-1], start):
        coords = list(reversed(coords))

    coords[0] = start
    coords[-1] = end
    return coords


def preferred_edge_attrs(
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
) -> dict | None:
    """Select a representative edge between `u` and `v`."""
    edge_dict = graph.get_edge_data(u, v)
    if not edge_dict:
        return None
    return min(
        edge_dict.values(),
        key=lambda data: data.get("length", float("inf")),
    )


def extract_geometry_coords(geometry: object) -> list[Coordinate] | None:
    """Return a mutable list of coordinates for the provided geometry."""
    if geometry is None:
        return None
    if hasattr(geometry, "coords"):
        return list(geometry.coords)  # type: ignore[return-value]
    if hasattr(geometry, "geoms"):
        coords: list[Coordinate] = []
        for geom in geometry.geoms:  # type: ignore[attr-defined]
            if hasattr(geom, "coords"):
                coords.extend(list(geom.coords))  # type: ignore[arg-type]
        return coords or None
    if isinstance(geometry, (list, tuple)):
        return list(geometry)
    return None


def squared_distance(a: Coordinate, b: Coordinate) -> float:
    """Return squared Euclidean distance between two lon/lat points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy
