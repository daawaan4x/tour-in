"""CLI entrypoint for exporting a routable graph to GeoJSON."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import orjson
from networkx.readwrite import json_graph

from tourin.graph.build_graph_geojson import build_graph_geojson

if TYPE_CHECKING:
    import networkx as nx

# region Configuration

LOGGER = logging.getLogger(__name__)
DEFAULT_GRAPH_JSON = Path("assets/ilocos_norte_graph_roads.json")
DEFAULT_OUTPUT = Path("assets/ilocos_norte_graph_roads.geojson")

# endregion Configuration


# region I/O Helpers


def _load_graph(graph_path: Path) -> nx.MultiGraph:
    """Load a graph JSON and return a NetworkX MultiGraph."""
    data = orjson.loads(graph_path.read_bytes())
    return json_graph.node_link_graph(data, multigraph=True, edges="edges")


def _write_geojson(data: dict, output_path: Path) -> None:
    """Write the GeoJSON FeatureCollection to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    LOGGER.info(
        "Exported GeoJSON to %s (%d bytes)",
        output_path,
        output_path.stat().st_size,
    )


# endregion I/O Helpers


# region CLI


def run_cli(args: argparse.Namespace) -> None:
    """Convert the serialized graph into GeoJSON and persist it."""
    graph = _load_graph(args.graph_json)
    geojson = build_graph_geojson(graph)
    _write_geojson(geojson, args.output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Return parsed CLI arguments for exporting GeoJSON."""
    parser = argparse.ArgumentParser(
        description="Convert a routable graph JSON into GeoJSON for QA.",
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
    parser.set_defaults(func=run_cli)
    return parser.parse_args(argv)


def _configure_logging() -> None:
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
