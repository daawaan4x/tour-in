"""Export a routable graph JSON into GeoJSON for validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    import networkx as nx


# region API


def build_graph_geojson(graph: nx.MultiGraph) -> dict:
    """Convert the routable graph into a GeoJSON FeatureCollection."""
    features = []

    # Nodes become Point features for quick inspection of intersections.
    for node_id, attrs in graph.nodes(data=True):
        lon = attrs.get("lon")
        lat = attrs.get("lat")
        if lon is None or lat is None:
            raise ValueError(f"Node {node_id} is missing lon/lat attributes.")
        node_props = {k: v for k, v in attrs.items() if k not in {"lon", "lat"}}
        node_props["node_id"] = node_id
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": node_props,
            },
        )

    # Edges become LineStrings; fall back to simple endpoints if needed.
    edge_iter = graph.edges(keys=True, data=True)

    for u, v, key, attrs in edge_iter:
        coords = attrs.get("coordinates") or _coords_from_nodes(graph, u, v)
        edge_props = {"u": u, "v": v, "edge_key": key}
        edge_props.update(
            {k: value for k, value in attrs.items() if k != "coordinates"},
        )
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": edge_props,
            },
        )

    return {"type": "FeatureCollection", "features": features}


# endregion API


# region Conversion helpers


def _coords_from_nodes(
    graph: nx.MultiGraph,
    u: int,
    v: int,
) -> Iterable[Iterable[float]]:
    """Fallback line geometry using only the endpoint coordinates."""
    u_data = graph.nodes[u]
    v_data = graph.nodes[v]
    return [
        [u_data["lon"], u_data["lat"]],
        [v_data["lon"], v_data["lat"]],
    ]


# endregion Conversion helpers
