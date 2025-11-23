from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import osmnx as ox

if TYPE_CHECKING:
    import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_GRAPH_FILE = ASSETS_DIR / "ilocos_norte_osmnx.graphml"


def setup_graph(graphml_path: str | Path | None = None) -> nx.MultiGraph:
    """Load the cached OSMnx graph and return its undirected representation.

    Parameters
    ----------
    graphml_path:
        Optional custom path to the GraphML file. When omitted, the default
        `assets/ilocos_norte_osmnx.graphml` file is used.

    Returns
    -------
    nx.MultiGraph
        An undirected NetworkX graph ready for path-finding algorithms.

    """
    path = Path(graphml_path) if graphml_path is not None else DEFAULT_GRAPH_FILE
    if not path.exists():
        msg = f"GraphML file not found: {path}"
        raise FileNotFoundError(msg)

    directed_graph = ox.load_graphml(path)

    # Drop directionality for easier routing.
    return ox.convert.to_undirected(directed_graph)
