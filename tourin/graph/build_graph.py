"""Routable graph builder for Ilocos Norte road data."""

from __future__ import annotations

import argparse
import collections.abc as cabc
import logging
import math
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import networkx as nx
import orjson
from networkx.readwrite import json_graph
from pyproj import Geod
from shapely.errors import TopologicalError
from shapely.geometry import LineString, Point
from shapely.ops import substring

# region Configuration & type aliases

Coordinate = tuple[float, float]
Breakpoints = dict[int, set[Coordinate]]

# Default CLI parameters for road extraction.
LOGGER = logging.getLogger(__name__)
DEFAULT_GEOJSON = Path("assets/ilocos_norte_osm_roads.geojson")
DEFAULT_GRAPH = Path("assets/ilocos_norte_graph_roads.json")
DEFAULT_MIN_SEGMENT_METERS = 0.0

# endregion Configuration & type aliases


# region Public API


def build_road_graph(
    geojson_path: Path,
    precision: int | None = None,
    min_segment_meters: float = DEFAULT_MIN_SEGMENT_METERS,
) -> nx.MultiGraph:
    """Return a weighted graph matching the provided road GeoJSON."""
    roads = _load_roads(geojson_path)
    geoms = roads.geometry.reset_index(drop=True)
    graph = nx.MultiGraph()
    geod = Geod(ellps="WGS84")
    node_lookup: dict[Coordinate, int] = {}
    breakpoints = _collect_breakpoints(geoms)

    for idx, line in enumerate(geoms):
        if line.is_empty:
            continue
        row = roads.iloc[idx]
        # Break the source line around true intersections/endpoints so each
        # segment represents a single traversable edge.
        segments = _segments_from_line(line, breakpoints[idx])
        metadata = {
            "way_id": _clean_value(row.get("osm_id")),
            "name": _clean_value(row.get("name")),
            "highway": _clean_value(row.get("highway")),
        }

        for start_coord, end_coord, coords in segments:
            length_m = _geodesic_length(coords, geod)
            if length_m <= min_segment_meters:
                continue

            u = _node_id(graph, node_lookup, start_coord, precision)
            v = _node_id(graph, node_lookup, end_coord, precision)

            edge_attr = {
                "weight": length_m,
                "length_m": length_m,
                "coordinates": [list(coord) for coord in coords],
                **metadata,
            }
            graph.add_edge(u, v, **edge_attr)

    LOGGER.info(
        "Graph built from %s with %s nodes / %s edges",
        geojson_path,
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )
    return graph


def serialize_graph(graph: nx.MultiGraph, output_path: Path) -> None:
    """Write the graph as node-link JSON for downstream tooling."""
    data = json_graph.node_link_data(graph, edges="edges")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    LOGGER.info(
        "Serialized graph to %s (%d bytes)",
        output_path,
        output_path.stat().st_size,
    )


# endregion Public API


# region Data loading helpers


def _load_roads(geojson_path: Path) -> gpd.GeoDataFrame:
    """Load road geometries and normalize them for processing."""
    roads = gpd.read_file(geojson_path)
    roads = roads[roads.geometry.notna()]
    roads = roads[roads.geom_type.isin(["LineString", "MultiLineString"])]
    if roads.empty:
        raise ValueError(f"No (Multi)LineString geometries found in {geojson_path}")
    roads = roads.explode(index_parts=False, ignore_index=True)
    roads = roads[~roads.is_empty]
    roads = _filter_positive_lengths(roads)
    return roads.reset_index(drop=True)


def _filter_positive_lengths(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter out zero-length geometries using a projected CRS where possible."""
    if roads.empty:
        return roads
    if roads.crs is None or roads.crs.is_projected:
        return roads[roads.length > 0]

    utm_crs = _utm_crs_for_bounds(roads)
    if utm_crs is None:
        LOGGER.warning(
            "Unable to determine UTM CRS; falling back to geographic length.",
        )
        return roads[roads.length > 0]

    try:
        projected = roads.to_crs(utm_crs)
        mask = projected.length > 0
        return roads[mask]
    except Exception as exc:  # pragma: no cover - last-resort guard
        LOGGER.warning(
            "Failed to reproject roads to %s (%s); falling back to geographic length.",
            utm_crs,
            exc,
        )
        return roads[roads.length > 0]


def _utm_crs_for_bounds(roads: gpd.GeoDataFrame) -> str | None:
    """Pick a UTM zone covering the dataset's centroid."""
    minx, miny, maxx, maxy = roads.total_bounds
    if not all(map(math.isfinite, (minx, miny, maxx, maxy))):
        return None
    lon = (minx + maxx) / 2.0
    lat = (miny + maxy) / 2.0
    zone = int(math.floor((lon + 180) / 6) + 1)
    hemisphere = "326" if lat >= 0 else "327"
    return f"EPSG:{hemisphere}{zone:02d}"


# endregion Data loading helpers


# region Geometry to graph conversion


def _collect_breakpoints(geoms: gpd.GeoSeries) -> Breakpoints:
    """Record endpoints + true intersections for each line to allow splitting."""
    breakpoints: Breakpoints = defaultdict(set)

    for idx, geom in enumerate(geoms):
        coords = list(geom.coords)
        if coords:
            breakpoints[idx].update((tuple(coords[0]), tuple(coords[-1])))

    # Spatially query for intersecting lines to capture shared vertices.
    sindex = geoms.sindex
    for idx, geom in enumerate(geoms):
        candidates = sindex.query(geom, predicate="intersects")
        for other_idx in candidates:
            if other_idx <= idx:
                continue
            other = geoms.iloc[other_idx]
            try:
                intersection = geom.intersection(other)
            except TopologicalError:
                continue
            for point in _points_from_geometry(intersection):
                coord = (point.x, point.y)
                breakpoints[idx].add(coord)
                breakpoints[other_idx].add(coord)
    return breakpoints


def _segments_from_line(
    line: LineString,
    coords: cabc.Iterable[Coordinate],
) -> list[tuple[Coordinate, Coordinate, list[Coordinate]]]:
    """Split a linestring into minimal segments between breakpoints."""
    ordered: list[tuple[float, Coordinate]] = []
    for coord in coords:
        point = Point(coord)
        ordered.append((float(line.project(point)), (float(point.x), float(point.y))))
    ordered.sort(key=lambda item: item[0])

    # Remove duplicate breakpoints that project to the same distance so we do
    # not create zero-length substrings.
    trimmed: list[tuple[float, Coordinate]] = []
    for distance, coord in ordered:
        if not trimmed or abs(distance - trimmed[-1][0]) > 1e-9:  # noqa: PLR2004
            trimmed.append((distance, coord))

    if not trimmed:
        return []

    trimmed = _ensure_terminal_breakpoints(line, trimmed)

    segments: list[tuple[Coordinate, Coordinate, list[Coordinate]]] = []
    for (start_dist, start_coord), (end_dist, end_coord) in _pairwise(trimmed):
        if end_dist - start_dist <= 1e-9:  # noqa: PLR2004
            continue
        segment = substring(line, start_dist, end_dist, normalized=False)
        if segment.is_empty:
            continue
        coords_list = [tuple(map(float, vertex)) for vertex in segment.coords]
        if len(coords_list) >= 2:  # noqa: PLR2004
            segments.append((start_coord, end_coord, coords_list))
    return segments


def _ensure_terminal_breakpoints(
    line: LineString,
    trimmed: list[tuple[float, Coordinate]],
) -> list[tuple[float, Coordinate]]:
    """Guarantee the start/end of a line are present in the breakpoint list."""
    start_coord = tuple(map(float, line.coords[0]))
    end_coord = tuple(map(float, line.coords[-1]))
    length = float(line.length)

    if abs(trimmed[0][0]) > 1e-9:  # noqa: PLR2004
        trimmed.insert(0, (0.0, start_coord))
    if abs(trimmed[-1][0] - length) > 1e-9:  # noqa: PLR2004
        trimmed.append((length, end_coord))
    return trimmed


# endregion Geometry to graph conversion


# region Utility helpers


def _points_from_geometry(geometry) -> list[Point]:  # noqa: ANN001
    """Return point representations for intersections of varying geometry types."""
    if geometry.is_empty:
        return []
    geom_type = geometry.geom_type
    if geom_type == "Point":
        return [geometry]
    if geom_type == "MultiPoint":
        return list(geometry.geoms)
    if geom_type in {"LineString", "LinearRing"}:
        coords = list(geometry.coords)
        return [Point(coords[0]), Point(coords[-1])]
    if geom_type == "MultiLineString":
        points: list[Point] = []
        for part in geometry.geoms:
            points.extend(_points_from_geometry(part))
        return points
    return []


def _node_id(
    graph: nx.MultiGraph,
    node_lookup: dict[Coordinate, int],
    coord: Coordinate,
    precision: int | None,
) -> int:
    """Return the node ID for a coordinate, creating one if necessary."""
    quantized = _quantize(coord, precision)
    if quantized not in node_lookup:
        node_id = len(node_lookup)
        node_lookup[quantized] = node_id
        graph.add_node(node_id, lon=quantized[0], lat=quantized[1])
    return node_lookup[quantized]


def _quantize(coord: Coordinate, precision: int | None) -> Coordinate:
    """Snap a coordinate to a fixed precision or keep its raw resolution."""
    if precision is None:
        return (float(coord[0]), float(coord[1]))
    return (round(coord[0], precision), round(coord[1], precision))


def _geodesic_length(coords: cabc.Sequence[Coordinate], geod: Geod) -> float:
    """Return the geodesic length of a polyline."""
    total = 0.0
    for (lon1, lat1), (lon2, lat2) in _pairwise(coords):
        _, _, distance = geod.inv(lon1, lat1, lon2, lat2)
        total += distance
    return total


def _pairwise(sequence: cabc.Sequence) -> cabc.Iterable[tuple]:
    """Yield consecutive pairs from the provided sequence."""
    for idx in range(len(sequence) - 1):
        yield sequence[idx], sequence[idx + 1]


def _clean_value(value):  # noqa: ANN001, ANN202
    """Normalize potentially nan/NumPy values to plain Python types."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # pragma: no cover - best effort
            return value
    return value


# endregion Utility helpers


# region CLI


def serialize_cli(args: argparse.Namespace) -> None:
    """Entry point for CLI invocations of the graph builder."""
    graph = build_road_graph(
        args.geojson,
        precision=args.precision,
        min_segment_meters=args.min_segment_meters,
    )
    serialize_graph(graph, args.output)


def parse_args(argv: cabc.Sequence[str] | None = None) -> argparse.Namespace:
    """Define CLI arguments for graph generation."""
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
    parser.set_defaults(func=serialize_cli)
    return parser.parse_args(argv)


def _configure_logging() -> None:
    """Configure a simple logging formatter for CLI runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: cabc.Sequence[str] | None = None) -> None:
    _configure_logging()
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

# endregion CLI
