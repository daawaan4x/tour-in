from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import osmnx as ox

if TYPE_CHECKING:
    import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_GRAPH_FILE = ASSETS_DIR / "ilocos_norte_osmnx.graphml"


def load_graph(graphml_path: str | Path | None = None) -> nx.MultiGraph:
    """Load the cached OSMnx graph and return its undirected representation.

    Parameters
    ----------
    graphml_path:
        Optional custom path to the GraphML file. When omitted, this loader
        checks `TOURIN_GRAPHML_PATH` then falls back to
        `assets/ilocos_norte_osmnx.graphml`.

    Returns
    -------
    nx.MultiGraph
        An undirected NetworkX graph ready for path-finding algorithms.

    """
    path = _resolve_graph_path(graphml_path).expanduser()
    if not path.exists():
        msg = f"GraphML file not found: {path}"
        raise FileNotFoundError(msg)

    directed_graph = ox.load_graphml(path)

    # Drop directionality for easier routing.
    return ox.convert.to_undirected(directed_graph)


def _resolve_graph_path(graphml_path: str | Path | None) -> Path:
    if graphml_path is not None:
        return Path(graphml_path)

    env_path = os.getenv("TOURIN_GRAPHML_PATH")
    if env_path is not None and env_path.strip():
        return Path(env_path)

    return DEFAULT_GRAPH_FILE
