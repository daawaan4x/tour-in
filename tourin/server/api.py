"""Flask API surface for exposing the route planner."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Hashable, Sequence

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from tourin.server.config import load_server_config
from tourin.server.graph.load import load_graph
from tourin.server.graph.snap import snap_coords
from tourin.server.graph.stitch import stitch_path
from tourin.server.search.ucs import plan as ucs_plan

Coordinate = tuple[float, float]


@dataclass(slots=True, frozen=True)
class DestinationRequest:
    """Normalized destination payload entry."""

    id: str
    coord: Coordinate


app = Flask(__name__)

CONFIG = load_server_config()
GRAPH = load_graph(CONFIG.graphml_path)


def _parse_coordinate(payload: object, label: str) -> Coordinate:
    """Validate that payload looks like {'lat': float, 'lon': float}."""
    if not isinstance(payload, dict):
        msg = f"{label} must be an object with 'lat' and 'lon'."
        raise BadRequest(msg)

    lat = payload.get("lat")
    lon = payload.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        msg = f"{label} must include numeric 'lat' and 'lon' fields."
        raise BadRequest(msg)

    return (float(lon), float(lat))


def _parse_destination(payload: object, label: str) -> DestinationRequest:
    if not isinstance(payload, dict):
        msg = f"{label} must be an object with 'id', 'lat', and 'lon'."
        raise BadRequest(msg)

    destination_id = payload.get("id")
    if not isinstance(destination_id, str) or not destination_id.strip():
        msg = f"{label} must include a non-empty string 'id' field."
        raise BadRequest(msg)

    return DestinationRequest(
        id=destination_id.strip(),
        coord=_parse_coordinate(payload, label),
    )


def _parse_destinations(payload: object) -> list[DestinationRequest]:
    if not isinstance(payload, list) or not payload:
        msg = "destinations must be a non-empty array of destination objects."
        raise BadRequest(msg)

    destinations = [
        _parse_destination(item, f"destinations[{index}]")
        for index, item in enumerate(payload)
    ]
    destination_ids = [destination.id for destination in destinations]
    if len(destination_ids) != len(set(destination_ids)):
        msg = "Destination ids must be unique."
        raise BadRequest(msg)

    return destinations


def _build_itinerary_order(
    visited_target_nodes: Sequence[Hashable],
    node_to_destination_ids: dict[Hashable, deque[str]],
    expected_total: int,
) -> list[str]:
    itinerary_order: list[str] = []

    for node_id in visited_target_nodes:
        destination_ids = node_to_destination_ids.get(node_id)
        if not destination_ids:
            msg = "Unable to map route visit order to destination ids."
            raise RuntimeError(msg)
        itinerary_order.append(destination_ids.popleft())

    if len(itinerary_order) != expected_total:
        msg = "Planner returned an unexpected destination visit count."
        raise RuntimeError(msg)

    if any(destination_ids for destination_ids in node_to_destination_ids.values()):
        msg = "Planner left unmapped destinations in the itinerary."
        raise RuntimeError(msg)

    return itinerary_order


@app.after_request
def _inject_cors(response: Response) -> Response:  # type: ignore[override]
    """Allow simple cross-origin requests from the browser frontend."""
    response.headers.setdefault(
        "Access-Control-Allow-Origin",
        CONFIG.cors_allowed_origin,
    )
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    response.headers.setdefault("Access-Control-Allow-Methods", "POST, OPTIONS")
    if CONFIG.cors_allowed_origin != "*":
        response.headers.setdefault("Vary", "Origin")
    return response


@app.route("/api/route", methods=["POST", "OPTIONS"])
def route_planner() -> Response:
    """Plan a route from a start point through the provided destinations."""
    if request.method == "OPTIONS":
        return Response("", status=204)

    raw_payload = request.get_json(silent=True)
    if raw_payload is None:
        payload: dict[str, object] = {}
    elif isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        msg = "Request body must be a JSON object."
        raise BadRequest(msg)

    try:
        start = _parse_coordinate(payload.get("start"), "start")
        destinations = _parse_destinations(payload.get("destinations"))
    except BadRequest:
        raise
    except Exception as exc:  # pragma: no cover - unexpected type mismatch
        msg = "Invalid request payload."
        raise BadRequest(msg) from exc

    graph = GRAPH
    destination_coords = [destination.coord for destination in destinations]

    try:
        snapped_nodes = snap_coords(graph, [start, *destination_coords])
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc

    start_node = snapped_nodes[0].node_id
    destination_snaps = snapped_nodes[1:]
    target_nodes = [node.node_id for node in destination_snaps]
    node_to_destination_ids: dict[Hashable, deque[str]] = defaultdict(deque)
    for destination, snapped in zip(destinations, destination_snaps, strict=True):
        node_to_destination_ids[snapped.node_id].append(destination.id)

    try:
        plan_result = ucs_plan(graph, start_node, target_nodes)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc

    stitched_path = stitch_path(graph, plan_result.node_path)
    itinerary_order = _build_itinerary_order(
        plan_result.visited_target_nodes,
        node_to_destination_ids,
        expected_total=len(destinations),
    )
    return jsonify(
        {
            "route": _serialize_coordinates(stitched_path),
            "itinerary_order": itinerary_order,
        },
    )


def _serialize_coordinates(coords: Sequence[Coordinate]) -> list[list[float]]:
    """Return JSON-serializable [lon, lat] coordinate lists."""
    return [[lon, lat] for lon, lat in coords]


if __name__ == "__main__":  # pragma: no cover
    app.run(port=CONFIG.port)
