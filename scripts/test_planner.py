from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import TextIO

from tourin.server.plan import plan

Coordinate = tuple[float, float]
FEATURE_COLLECTION_TYPE = "FeatureCollection"
POINT_TYPE = "Point"
MIN_COORDINATE_COMPONENTS = 2
MIN_POINT_FEATURES = 2


def echo(message: str = "", *, stream: TextIO = sys.stdout) -> None:
    """Write a line to the chosen stream and flush immediately."""
    stream.write(f"{message}\n")
    stream.flush()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Create a temporary GeoJSON file for point features, then plan a route "
            "where the first point is the start and the remaining points are the "
            "destinations."
        ),
    )
    parser.add_argument(
        "-d",
        "--directory",
        default=".",
        help="Directory where the temporary GeoJSON file will be created.",
    )
    return parser.parse_args()


def create_temp_geojson_file(directory: Path) -> Path:
    """Create an empty, uniquely named GeoJSON file for the user to edit."""
    directory.mkdir(parents=True, exist_ok=True)
    temp_path = directory / f"points-{uuid.uuid4().hex}.geojson"
    temp_path.write_text("", encoding="utf-8")
    return temp_path


def wait_for_user_to_fill(path: Path) -> None:
    """Tell the user to populate the GeoJSON file and pause execution."""
    echo(f"Paste your GeoJSON FeatureCollection of Point features into: {path}")
    echo("Save the file, then return here.")
    input("Press Enter to continue once the file is ready...")


def cleanup_file(path: Path) -> None:
    """Remove the temporary GeoJSON file."""
    try:
        path.unlink()
    except FileNotFoundError:
        return


def load_feature_collection(path: Path) -> dict:
    """Load and validate that the JSON document is a FeatureCollection."""
    raw_contents = path.read_text(encoding="utf-8").strip()
    if not raw_contents:
        raise ValueError("The GeoJSON file is still empty.")

    try:
        document = json.loads(raw_contents)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to parse JSON: {exc}") from exc

    if document.get("type") != FEATURE_COLLECTION_TYPE:
        raise ValueError("GeoJSON must be a FeatureCollection.")

    features = document.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("FeatureCollection must contain at least one feature.")

    return document


def extract_coordinate(feature: dict, index: int) -> Coordinate:
    """Return a coordinate tuple from the feature's geometry."""
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise TypeError(f"Feature #{index} is missing its geometry.")

    if geometry.get("type") != POINT_TYPE:
        raise ValueError(f"Feature #{index} must be a Point geometry.")

    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, (list, tuple)):
        raise TypeError(f"Feature #{index} coordinates must be a list or tuple.")
    if len(coordinates) < MIN_COORDINATE_COMPONENTS:
        raise ValueError(f"Feature #{index} is missing longitude/latitude values.")

    try:
        lon = float(coordinates[0])
        lat = float(coordinates[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Feature #{index} coordinates must be numeric.") from exc

    return lon, lat


def parse_points_from_geojson(path: Path) -> tuple[Coordinate, list[Coordinate]]:
    """Read the start and destination points from the GeoJSON file."""
    document = load_feature_collection(path)
    features = document["features"]

    coordinates = [
        extract_coordinate(feature, idx + 1) for idx, feature in enumerate(features)
    ]

    if len(coordinates) < MIN_POINT_FEATURES:
        raise ValueError("Provide at least two Point features (start + destination).")

    start = coordinates[0]
    destinations = coordinates[1:]
    return start, destinations


def build_geojson(
    start: Coordinate,
    destinations: list[Coordinate],
    path: list[Coordinate],
) -> dict:
    """Create a GeoJSON feature collection describing the route."""
    features = [
        {
            "type": "Feature",
            "properties": {"role": "start"},
            "geometry": {"type": "Point", "coordinates": start},
        },
    ]

    for idx, destination in enumerate(destinations, start=1):
        features.append(
            {
                "type": "Feature",
                "properties": {"role": "destination", "index": idx},
                "geometry": {"type": "Point", "coordinates": destination},
            },
        )

    features.append(
        {
            "type": "Feature",
            "properties": {"role": "path"},
            "geometry": {"type": "LineString", "coordinates": path},
        },
    )

    return {"type": "FeatureCollection", "features": features}


def main() -> None:
    """Entry point for the GeoJSON-driven CLI."""
    args = parse_args()
    directory = Path(args.directory).expanduser().resolve()
    temp_path = create_temp_geojson_file(directory)

    echo(f"Created temporary GeoJSON file at: {temp_path}")

    try:
        wait_for_user_to_fill(temp_path)
        start, destinations = parse_points_from_geojson(temp_path)
    except KeyboardInterrupt:
        echo()
        echo("Aborted by user.")
        sys.exit(1)
    except ValueError as exc:
        echo(f"Invalid GeoJSON input: {exc}", stream=sys.stderr)
        sys.exit(1)
    finally:
        cleanup_file(temp_path)

    path = plan(start, destinations)
    geojson = build_geojson(start, destinations, path)

    echo()
    echo(json.dumps(geojson))


if __name__ == "__main__":
    main()
