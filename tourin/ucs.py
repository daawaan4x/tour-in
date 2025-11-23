"""Uniform Cost Search (UCS) planner for visiting multiple destinations."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import pairwise
from typing import TYPE_CHECKING, Hashable, Iterable, Sequence

from .geo import great_circle_meters
from .logger import Logger
from .snap import SNAP_MAX_DISTANCE_M, snap_coords

if TYPE_CHECKING:
    import networkx as nx

Coordinate = tuple[float, float]  # (lon, lat)


@dataclass(slots=True)
class UCSResult:
    """Container for a UCS leg result."""

    target: Hashable
    path: list[Hashable]
    cost: float


def plan(
    graph: nx.MultiGraph,
    start: Coordinate,
    destinations: Sequence[Coordinate],
    logger: Logger = Logger(),  # noqa: B008
) -> list[Coordinate]:
    """Generate a LineString route that visits all destinations.

    Parameters
    ----------
    graph:
        Undirected OSMnx graph (output of `setup_graph`).
    start:
        Starting `(lon, lat)` coordinate.
    destinations:
        Sequence of `(lon, lat)` destination coordinates to visit.
    logger:
        Logger controlling status/timing output. Defaults to a silent logger.

    Returns
    -------
    list[Coordinate]
        LineString containing the stitched path coordinates
        (lon, lat order).

    Notes
    -----
    This function calculates the shortest route to visit all destinations by
    rerunning UCS from the current node after each visited destination.

    """
    if not destinations:
        msg = "At least one destination coordinate is required."
        raise ValueError(msg)

    snap_phase = logger.phase(
        "snap.coords",
        coords=len(destinations) + 1,
        max_distance_m=SNAP_MAX_DISTANCE_M,
    )
    with snap_phase:
        snapped_points = snap_coords(
            graph,
            [start, *destinations],
            max_distance_m=SNAP_MAX_DISTANCE_M,
        )
    start_node = snapped_points[0].node_id
    pending_targets = {snap.node_id for snap in snapped_points[1:]}

    # Track the accumulated node path; reuse junction nodes only once.
    full_path: list[Hashable] = [start_node]
    current_node = start_node

    logger.info(
        "search.initialized",
        requested=len(destinations),
        unique_pending=len(pending_targets),
    )

    search_phase = logger.phase(
        "search.run",
        legs=len(destinations),
    )

    with search_phase:
        while pending_targets:
            logger.info(
                "search.leg.start",
                origin=current_node,
                remaining=len(pending_targets),
            )
            result = _ucs(graph, current_node, pending_targets)
            if result is None:
                msg = "No route found for remaining destinations."
                raise RuntimeError(msg)
            _, path = result.target, result.path
            full_path.extend(path[1:])  # avoid duplicating junction node
            pending_targets.remove(result.target)
            current_node = result.target
            logger.info(
                "search.leg.complete",
                reached=result.target,
                leg_cost=f"{result.cost:.1f}",
                remaining=len(pending_targets),
            )

    stitch_phase = logger.phase(
        "stitch.path",
        nodes=len(full_path),
    )
    with stitch_phase:
        path_coords = _path_coordinates(graph, full_path)

    logger.info("route.ready", coordinates=len(path_coords))

    return path_coords


def _ucs(
    graph: nx.MultiGraph,
    source: Hashable,
    targets: Iterable[Hashable],
) -> UCSResult | None:
    """Run UCS until the closest target node is reached."""
    target_set = set(targets)
    frontier: list[tuple[float, Hashable, list[Hashable]]] = [
        (0.0, source, [source]),
    ]
    # best_cost caches the cheapest known cost to each node to avoid rework.
    best_cost = {source: 0.0}

    while frontier:
        cost, node, path = heappop(frontier)
        if node in target_set:
            return UCSResult(target=node, path=path, cost=cost)

        if cost > best_cost.get(node, float("inf")):
            continue

        for neighbor in graph.neighbors(node):
            step_cost = _edge_travel_cost(graph, node, neighbor)
            new_cost = cost + step_cost
            if new_cost < best_cost.get(neighbor, float("inf")):
                best_cost[neighbor] = new_cost
                heappush(frontier, (new_cost, neighbor, [*path, neighbor]))

    return None


def _edge_travel_cost(
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
) -> float:
    """Return the travel cost between two adjacent nodes."""
    candidate = _preferred_edge_attrs(graph, u, v)
    if candidate is None:
        return float("inf")

    length = candidate.get("length")
    if length is not None:
        return float(length)

    # When the edge lacks a precomputed length, approximate using coordinates.
    u_geo = graph.nodes[u]
    v_geo = graph.nodes[v]
    return great_circle_meters(u_geo["y"], u_geo["x"], v_geo["y"], v_geo["x"])


def _path_coordinates(
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
        segment = _edge_geometry_coords(graph, u, v)
        # Skip the first coordinate to avoid duplicates.
        stitched.extend(segment[1:])

    return stitched


def _edge_geometry_coords(
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
) -> list[Coordinate]:
    """Return the geometry coordinates between adjacent nodes."""
    candidate = _preferred_edge_attrs(graph, u, v)
    start = (graph.nodes[u]["x"], graph.nodes[u]["y"])
    end = (graph.nodes[v]["x"], graph.nodes[v]["y"])

    if candidate is None:
        return [start, end]

    coords = _extract_geometry_coords(candidate.get("geometry"))
    if not coords:
        return [start, end]

    # Ensure polyline runs from node `u` to node `v` and touches their exact coordinates.
    if _squared_distance(coords[0], start) > _squared_distance(coords[-1], start):
        coords = list(reversed(coords))

    coords[0] = start
    coords[-1] = end
    return coords


def _preferred_edge_attrs(
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


def _extract_geometry_coords(geometry: object) -> list[Coordinate] | None:
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


def _squared_distance(a: Coordinate, b: Coordinate) -> float:
    """Return squared Euclidean distance between two lon/lat points."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy
