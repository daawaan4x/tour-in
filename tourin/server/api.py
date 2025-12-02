"""Flask API surface for exposing the route planner."""

from __future__ import annotations

from typing import Sequence

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import BadRequest

from tourin.server.graph.load import load_graph
from tourin.server.graph.snap import snap_coords
from tourin.server.graph.stitch import stitch_path
from tourin.server.search.ucs import plan as ucs_plan

Coordinate = tuple[float, float]

app = Flask(__name__)

GRAPH = load_graph()


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


def _parse_destinations(payload: object) -> list[Coordinate]:
    if not isinstance(payload, list) or not payload:
        msg = "destinations must be a non-empty array of coordinates."
        raise BadRequest(msg)

    return [
        _parse_coordinate(item, f"destinations[{index}]")
        for index, item in enumerate(payload)
    ]


@app.after_request
def _inject_cors(response: Response) -> Response:  # type: ignore[override]
    """Allow simple cross-origin requests from the browser frontend."""
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
    response.headers.setdefault("Access-Control-Allow-Methods", "POST, OPTIONS")
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

    try:
        snapped_nodes = snap_coords(graph, [start, *destinations])
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc

    start_node = snapped_nodes[0].node_id
    target_nodes = [node.node_id for node in snapped_nodes[1:]]

    try:
        node_path = ucs_plan(graph, start_node, target_nodes)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc

    stitched_path = stitch_path(graph, node_path)
    return jsonify({"route": _serialize_coordinates(stitched_path)})


def _serialize_coordinates(coords: Sequence[Coordinate]) -> list[list[float]]:
    """Return JSON-serializable [lon, lat] coordinate lists."""
    return [[lon, lat] for lon, lat in coords]


if __name__ == "__main__":  # pragma: no cover
    app.run()