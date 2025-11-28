"""Uniform Cost Search (UCS) planner for visiting multiple destinations."""

from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import TYPE_CHECKING, Hashable, Iterable, Sequence

from tourin.server.graph.stitch import preferred_edge_attrs
from tourin.server.utils.geo import great_circle_meters

if TYPE_CHECKING:
    import networkx as nx


@dataclass(slots=True)
class UCSResult:
    """Container for a UCS leg result."""

    target: Hashable
    path: list[Hashable]
    cost: float


def plan(
    graph: nx.MultiGraph,
    start_node: Hashable,
    target_nodes: Sequence[Hashable],
) -> list[Hashable]:
    """Plan the node sequence that visits all destinations via UCS."""
    if not target_nodes:
        msg = "At least one destination coordinate is required."
        raise ValueError(msg)

    pending_targets = {*target_nodes}

    # Track the accumulated node path; reuse junction nodes only once.
    full_path: list[Hashable] = [start_node]
    current_node = start_node

    while pending_targets:
        result = _ucs(graph, current_node, pending_targets)
        if result is None:
            msg = "No route found for remaining destinations."
            raise RuntimeError(msg)
        _, path = result.target, result.path
        full_path.extend(path[1:])  # avoid duplicating junction node
        pending_targets.remove(result.target)
        current_node = result.target

    return full_path


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
    candidate = preferred_edge_attrs(graph, u, v)
    if candidate is None:
        return float("inf")

    length = candidate.get("length")
    if length is not None:
        return float(length)

    # When the edge lacks a precomputed length, approximate using coordinates.
    u_geo = graph.nodes[u]
    v_geo = graph.nodes[v]
    return great_circle_meters(u_geo["y"], u_geo["x"], v_geo["y"], v_geo["x"])
