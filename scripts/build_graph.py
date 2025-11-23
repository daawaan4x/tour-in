"""CLI entrypoint for building the Ilocos Norte routable graph."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Sequence

import geopandas as gpd
import orjson

from tourin.graph.build_graph import (
    DEFAULT_MIN_SEGMENT_METERS,
    build_graph,
    prepare_roads,
    serialize_graph,
)

# region Configuration

LOGGER = logging.getLogger(__name__)
DEFAULT_GEOJSON = Path("assets/ilocos_norte_osm_roads.geojson")
DEFAULT_GRAPH = Path("assets/ilocos_norte_graph_roads.json")

# endregion Configuration


# region I/O Helpers


def _load_geodata(geojson_path: Path) -> gpd.GeoDataFrame:
    """Load a road network GeoJSON and return a NetworkX MultiGraph."""
    roads = gpd.read_file(geojson_path)
    return prepare_roads(roads)


def _write_json(data: dict, output_path: Path) -> None:
    """Persist the node-link graph representation to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    LOGGER.info(
        "Serialized graph to %s (%d bytes)",
        output_path,
        output_path.stat().st_size,
    )


# endregion I/O Helpers


# region CLI


def run_cli(args: argparse.Namespace) -> None:
    """Build the routable graph using on-disk GeoJSON inputs."""
    roads = _load_geodata(args.geojson)
    graph = build_graph(
        roads,
        precision=args.precision,
        min_segment_meters=args.min_segment_meters,
    )
    json = serialize_graph(graph)
    _write_json(json, args.output)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Return parsed CLI arguments for graph building."""
    parser = argparse.ArgumentParser(
        description="Convert Ilocos Norte roads into a routable graph.",
    )
    parser.add_argument(
        "--geojson",
        type=Path,
        default=DEFAULT_GEOJSON,
        help="Path to the road GeoJSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_GRAPH,
        help="Destination path for the serialized graph (.json).",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=None,
        help="Decimal places to snap node coordinates (default: preserve raw precision).",  # noqa: E501
    )
    parser.add_argument(
        "--min-segment-meters",
        type=float,
        default=DEFAULT_MIN_SEGMENT_METERS,
        help="Drop road segments shorter than this many meters (default: 0 to keep all).",  # noqa: E501
    )
    parser.set_defaults(func=run_cli)
    return parser.parse_args(argv)


def _configure_logging() -> None:
    """Configure a simple logging formatter for CLI runs."""
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
