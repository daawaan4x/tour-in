"""Export a routable graph JSON into GeoJSON for validation."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, Iterable, Sequence

import networkx as nx
import orjson
from networkx.readwrite import json_graph

# region Configuration & constants

LOGGER = logging.getLogger(__name__)
DEFAULT_GRAPH_JSON = Path("assets/ilocos_norte_graph_roads.json")
DEFAULT_OUTPUT = Path("assets/ilocos_norte_graph_roads.geojson")

# endregion Configuration & constants


# region Conversion helpers


def graph_to_geojson(graph: nx.Graph) -> Dict:
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
            }
        )

    # Edges become LineStrings; fall back to simple endpoints if needed.
    for u, v, attrs in graph.edges(data=True):
        coords = attrs.get("coordinates") or _coords_from_nodes(graph, u, v)
        edge_props = {"u": u, "v": v}
        edge_props.update(
            {k: value for k, value in attrs.items() if k != "coordinates"}
        )
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": edge_props,
            }
        )

    return {"type": "FeatureCollection", "features": features}


def _coords_from_nodes(graph: nx.Graph, u: int, v: int) -> Iterable[Iterable[float]]:
    """Fallback line geometry using only the endpoint coordinates."""
    u_data = graph.nodes[u]
    v_data = graph.nodes[v]
    return [
        [u_data["lon"], u_data["lat"]],
        [v_data["lon"], v_data["lat"]],
    ]


# endregion Conversion helpers


# region I/O helpers


def load_graph(graph_path: Path) -> nx.Graph:
    """Load a node-link JSON graph from disk."""
    data = orjson.loads(graph_path.read_bytes())
    return json_graph.node_link_graph(data)


def write_geojson(data: Dict, output_path: Path) -> None:
    """Write the GeoJSON FeatureCollection to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    LOGGER.info(
        "Exported GeoJSON to %s (%d bytes)", output_path, output_path.stat().st_size
    )


# endregion I/O helpers


# region CLI


def export_cli(args: argparse.Namespace) -> None:
    """CLI entry point for exporting a graph JSON to GeoJSON."""
    graph = load_graph(args.graph_json)
    geojson = graph_to_geojson(graph)
    write_geojson(geojson, args.output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the GeoJSON exporter."""
    parser = argparse.ArgumentParser(
        description="Convert a routable graph JSON into GeoJSON for QA."
    )
    parser.add_argument(
        "--graph-json",
        type=Path,
        default=DEFAULT_GRAPH_JSON,
        help="Path to the serialized graph JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination GeoJSON for validation.",
    )
    parser.set_defaults(func=export_cli)
    return parser.parse_args(argv)


def _configure_logging():
    """Configure default logging for CLI usage."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point."""
    _configure_logging()
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

# endregion CLI
