"""Helpers for snapping arbitrary coordinates onto an OSMnx routing graph."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import TYPE_CHECKING, Hashable, Literal, Sequence
from uuid import uuid4

import numpy as np
import osmnx as ox
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge, substring

from tourin.server.utils.geo import Coordinate, great_circle_meters

if TYPE_CHECKING:
    import networkx as nx

# (u, v, key) triple length used by NetworkX MultiGraphs.
EDGE_TUPLE_SIZE = 3
# When splitting an edge by a perpendicular projection we expect two segments.
EXPECTED_SEGMENT_COUNT = 2
# Minimum coordinate count required for a valid LineString segment.
MIN_LINESTRING_COORDS = 2
# Default maximum snapping distance in meters.
SNAP_MAX_DISTANCE_M = 100.0


@dataclass(slots=True)
class SnapResult:
    """Describes how an arbitrary coordinate was snapped onto the graph."""

    original: Coordinate
    node_id: Hashable
    snapped: Coordinate
    method: Literal["node", "edge"]
    distance_m: float


def snap_coords(
    graph: nx.MultiGraph,
    coords: Sequence[Coordinate],
    max_distance_m: float | None = SNAP_MAX_DISTANCE_M,
) -> list[SnapResult]:
    """Snap (lon, lat) coordinates onto graph nodes or edges.

    Parameters
    ----------
    graph:
        The working OSMnx/NetworkX graph rendered undirected via `setup_graph`.
    coords:
        Sequence of `(lon, lat)` coordinate pairs to snap.
    max_distance_m:
        Maximum allowed snapping distance (meters). Coordinates farther than
        this distance from any graph element raise ``ValueError``. Set to
        ``None`` to disable the guard.

    Returns
    -------
    list[SnapResult]
        Metadata describing the snapped location for each input coordinate.

    Notes
    -----
    Any coordinate that falls closer to an edge than an existing node triggers
    a synthetic node insertion along that edge so subsequent routing algorithms
    can operate purely on graph nodes.

    """
    if not coords:
        return []

    # Collect candidate nodes/edges in a single batch for performance.
    lons, lats = zip(*coords)
    node_ids_raw, node_dists_raw = ox.distance.nearest_nodes(
        graph,
        X=lons,
        Y=lats,
        return_dist=True,
    )
    edge_ids_raw, edge_dists_raw = ox.distance.nearest_edges(
        graph,
        X=lons,
        Y=lats,
        return_dist=True,
    )

    node_ids = _ensure_list(node_ids_raw)
    node_dists = _ensure_list(node_dists_raw)
    edge_ids = _ensure_edge_list(edge_ids_raw)
    edge_dists = _ensure_list(edge_dists_raw)

    snapped: list[SnapResult] = []

    for idx, (lon, lat) in enumerate(coords):
        node_id = node_ids[idx]
        node_dist = node_dists[idx]
        edge_tuple = edge_ids[idx]
        edge_dist = edge_dists[idx]

        nearest_distance = node_dist if edge_dist is None else min(node_dist, edge_dist)
        if max_distance_m is not None and nearest_distance > max_distance_m:
            msg = (
                "Coordinate is too far from the routing graph: "
                f"{nearest_distance:.1f}m > {max_distance_m:.1f}m for {(lon, lat)}"
            )
            raise ValueError(msg)

        if edge_dist is None or node_dist <= edge_dist:
            snapped_node_id = node_id
            method: Literal["node", "edge"] = "node"
        else:
            snapped_node_id = _insert_synthetic_node(
                graph,
                edge_tuple,
                Point(lon, lat),
            )
            method = "edge"

        node_data = graph.nodes[snapped_node_id]
        snapped_lat = node_data["y"]
        snapped_lon = node_data["x"]
        distance = great_circle_meters(lat, lon, snapped_lat, snapped_lon)

        snapped.append(
            SnapResult(
                original=(lon, lat),
                node_id=snapped_node_id,
                snapped=(snapped_lon, snapped_lat),
                method=method,
                distance_m=distance,
            ),
        )

    return snapped


def _ensure_list(value: object) -> list:
    """Return a plain list regardless of whether `value` is scalar/tuple/array."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _ensure_edge_list(
    value: object,
) -> list[tuple[Hashable, Hashable, int]]:
    """Normalize the varied return shapes from `ox.distance.nearest_edges`."""
    if isinstance(value, np.ndarray):
        flattened = value.tolist()
        if not isinstance(flattened, (list, tuple)):
            flattened = [flattened]
        # When the array represents a single edge, `tolist` returns a flat list
        # of scalars (e.g., [u, v, key]). Wrap it so callers can index per edge.
        if isinstance(flattened, list) and flattened:
            first = flattened[0]
            if not isinstance(first, (list, tuple, np.ndarray)):
                return [tuple(flattened)]  # type: ignore[list-item]
        if isinstance(flattened, tuple) and len(flattened) == EDGE_TUPLE_SIZE:
            return [flattened]
        return [
            tuple(item) if isinstance(item, (list, tuple, np.ndarray)) else (item,)
            for item in flattened
        ]
    if isinstance(value, tuple) and len(value) == EDGE_TUPLE_SIZE:
        return [value]
    return [tuple(edge) for edge in value]  # type: ignore[arg-type]


def _insert_synthetic_node(
    graph: nx.MultiGraph,
    edge: tuple[Hashable, Hashable, int],
    target_point: Point,
) -> Hashable:
    """Split an edge and insert a synthetic node nearest to `target_point`."""
    u, v, key = edge
    edge_attrs = dict(graph[u][v][key])
    line = _edge_geometry(graph, u, v, edge_attrs)
    projected_point, distance_along = _project_point(line, target_point)

    segment_list = _split_line_segments(line, distance_along)
    if len(segment_list) != EXPECTED_SEGMENT_COUNT:
        # Degenerate case: fallback to whichever endpoint is closer.
        dist_to_u = projected_point.distance(
            Point(graph.nodes[u]["x"], graph.nodes[u]["y"]),
        )
        dist_to_v = projected_point.distance(
            Point(graph.nodes[v]["x"], graph.nodes[v]["y"]),
        )
        return u if dist_to_u <= dist_to_v else v

    first, second = _orient_segments(segment_list, graph, u, v)

    new_node_id = f"snap-{uuid4().hex}"
    # Store longitude/latitude for compatibility with OSMnx helper functions.
    graph.add_node(
        new_node_id,
        x=projected_point.x,
        y=projected_point.y,
        lon=projected_point.x,
        lat=projected_point.y,
        synthetic=True,
    )

    graph.remove_edge(u, v, key)

    first_attrs = edge_attrs.copy()
    first_attrs["geometry"] = first
    first_attrs["length"] = _linestring_length(first)
    graph.add_edge(u, new_node_id, **first_attrs)

    second_attrs = edge_attrs.copy()
    second_attrs["geometry"] = second
    second_attrs["length"] = _linestring_length(second)
    graph.add_edge(new_node_id, v, **second_attrs)

    return new_node_id


def _edge_geometry(
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
    attrs: dict,
) -> LineString:
    """Return a `LineString` representing the edge geometry."""
    geometry = attrs.get("geometry")
    if isinstance(geometry, LineString):
        return geometry
    if isinstance(geometry, MultiLineString):
        merged = linemerge(geometry)
        if isinstance(merged, LineString):
            return merged
    start = (graph.nodes[u]["x"], graph.nodes[u]["y"])
    end = (graph.nodes[v]["x"], graph.nodes[v]["y"])
    return LineString([start, end])


def _project_point(line: LineString, point: Point) -> tuple[Point, float]:
    """Project `point` onto `line` and return the closest point and distance."""
    distance_along = line.project(point)
    projected_point = line.interpolate(distance_along)
    return projected_point, distance_along


def _split_line_segments(line: LineString, split_distance: float) -> list[LineString]:
    """Return line fragments obtained by cutting `line` at `split_distance`."""
    line_length = line.length
    if line_length == 0 or split_distance <= 0 or split_distance >= line_length:
        return []

    first = substring(line, 0, split_distance)
    second = substring(line, split_distance, line_length)

    segments: list[LineString] = []
    for segment in (first, second):
        if isinstance(segment, LineString) and not segment.is_empty:
            coords = list(segment.coords)
            if len(coords) >= MIN_LINESTRING_COORDS:
                segments.append(segment)
    return segments


def _linestring_length(line: LineString) -> float:
    """Compute the great-circle length of a line storing lon/lat coordinates."""
    coords = list(line.coords)
    total = 0.0
    for (x1, y1), (x2, y2) in pairwise(coords):
        total += great_circle_meters(y1, x1, y2, x2)
    return total


def _orient_segments(
    segments: list[LineString],
    graph: nx.MultiGraph,
    u: Hashable,
    v: Hashable,
) -> tuple[LineString, LineString]:
    """Order edge fragments so they connect `u -> new_node -> v`."""
    u_point = Point(graph.nodes[u]["x"], graph.nodes[u]["y"])
    v_point = Point(graph.nodes[v]["x"], graph.nodes[v]["y"])

    first = min(segments, key=lambda seg: seg.distance(u_point))
    second = min(segments, key=lambda seg: seg.distance(v_point))
    if first == second:
        # Fall back to original ordering if both mins refer to the same segment.
        first, second = segments[:EXPECTED_SEGMENT_COUNT]
    return first, second
