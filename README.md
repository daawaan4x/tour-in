# `TOUR-IN` for MMSU-CS162

App for finding the shortest path to tour places around Ilocos Norte — made with Python.

## Features

- Select multiple Points of Interest (POIs) to visit
- Start path from any starting location

## Contributor

In alphabetical order:

- [Gartly Cortez](https://github.com/Toshihiro20) (@Toshihiro20)
- JM Benito
- [Theone Eclarin](https://github.com/daawaan4x) (@daawaan4x)

## Table of Contents

1. [User Manual](#user-manual)
   - [Setup & Installation](#setup--installation)
   - [Graph Preparation](#graph-preparation)
2. [Algorithm](#algorithm)
   - [Manual Testing](#manual-testing)

## User Manual

### Setup & Installation

**Recommended**: Install `Python 3.10` using a version manager such as `pyenv` from https://github.com/pyenv/pyenv/ (Unix) or https://github.com/pyenv-win/pyenv-win (Windows).

Alternatively, you can install python packages from https://www.python.org/downloads/.

**Recommended**: After setting up your python installation, install the project's dependencies in a virtual environment. Visit `venv` docs from https://docs.python.org/3/library/venv.html for more information:

```sh
cd <this-project-folder>

python -m venv .venv

# --- UNIX ---
source .venv/bin/activate # bash/zsh
.venv/bin/Activate.ps1 # Powershell

# --- Windows ---
source .venv/Scripts/activate # bash/zsh
.venv\Scripts\activate.bat # Command Prompt
.venv\Scripts\Activate.ps1 # Powershell

pip install -r requirements.txt
```

### Graph Preparation

Before the app can run search algorithms, a routable graph of the original _OpenStreetMap_ data has to be created first. The project already comes with pre-downloaded & pre-processed map data ready for routing. Run the following command to redownloaded the file(s) if necessary.

```sh
python ./scripts/download_osmnx_graph.py
```

### Development Server

Start both the Flask API (Python) and the Vite frontend so the browser can reach the planner endpoint. The examples below assume you already installed the Python and Node dependencies described earlier.

#### 1. Flask API

Open a terminal in the project root, activate your virtual environment, then launch Flask with a single command:

```sh
cd <this-project-folder>

# Activate your virtual environment here

flask --app tourin.server.api --debug run
```

#### 2. Vite Frontend

In a separate terminal, install the web dependencies (once) and launch the dev server. By default it should point straight to the Flask app above; override `VITE_API_BASE` in a `.env.local` file if you host the API elsewhere.

```sh
cd <this-project-folder>

pnpm install    # or npm install / yarn install
pnpm dev
```

## Algorithm

The route planner flows through a four-stage pipeline: it loads a cached Ilocos Norte road network graph, snaps the start & destination coordinates onto that road network, runs a uniform-cost search to order and connect the visits, and finally stitches the visited nodes back into the actual road geometry.

### Loading the Graph

`tourin/server/graph/load.py` uses OSMnx to keep a preprocessed GraphML file (fetched via `scripts/download_osmnx_graph.py`) optimized for routing. The GraphML file has a simplified topology with the actual geometry of the roads preserved. The loader validates that the file exists, opens it once, and converts the directed graph to an undirected graph to simplify the search algorithms used in this project.

```
function load_graph():
  ensure_exists(default_path)
  directed = ox.load_graphml(default_path)
  return ox.convert.to_undirected(directed)
```

### Snapping Input Coordinates to the Graph

Before searching, `snap_coords` projects the raw `(lon, lat)` inputs onto the nearest nodes or edges. If a point falls closer to the middle of an edge, that edge is split and a synthetic node is inserted so every search algorithm downstream works purely with node IDs. A maximum snapping distance guard prevents impossible requests e.g. start/destination coordinates that are too far from any road.

```
function snap_coords(graph, coords):
  snaps = []
  for coord in coords:
    nearest_node = ox.nearest_node(graph, coord)
    nearest_edge = ox.nearest_edge(graph, coord)
    if edge_is_closer(nearest_node, nearest_edge):
      node_id = split_edge_with_synthetic_node(graph, nearest_edge, coord)
    else:
      node_id = nearest_node
    snaps.append(node_id)
  return snaps
```

To keep edge splits simple, a helper inserts a synthetic node wherever the projection falls along the middle of a road segment and rewires the surrounding edges so the graph stays routable:

```
function split_edge_with_synthetic_node(graph, edge, coord):
  (u, v, key) = edge
  geometry = edge_geometry(graph, u, v, key)
  projected_point = project_point_onto_geometry(geometry, coord)
  (first_segment, second_segment) = split_geometry(geometry, projected_point)

  new_node = graph.add_node(lon=projected_point.x, lat=projected_point.y)
  graph.remove_edge(u, v, key)
  graph.add_edge(u, new_node, geometry=first_segment)
  graph.add_edge(new_node, v, geometry=second_segment)
  return new_node
```

### Running the Search Algorithm

`tourin/server/search/ucs.py` implements a multi-destination Uniform Cost Search (UCS). Starting from the start node, it repeatedly expands the cheapest frontier until the closest remaining destination is reached, appends the traversed path to the full itinerary, and restarts the search from the most recent target node until every target is covered. Edge costs rely on the distances between nodes, so the planner naturally favors shorter travel.

```
function plan_route(graph, start_node, target_nodes):
  pending = set(target_nodes)
  full_path = [start_node]
  current = start_node

  while pending:
    result = uniform_cost_search(graph, current, pending)
    full_path.extend(result.path[1:])
    pending.remove(result.target)
    current = result.target

  return full_path
```

The underlying UCS loop is still lightweight: it prioritizes the cheapest frontier entry, stops as soon as a target is reached, and keeps a best-cost cache to avoid re-exploring expensive detours.

```
function uniform_cost_search(graph, source, targets):
  frontier = priority_queue()
  frontier.push(cost=0, node=source, path=[source])
  best_cost = {source: 0}

  while frontier not empty:
    (cost, node, path) = frontier.pop_lowest()
    if node in targets: return {target: node, path: path, cost: cost}
    if cost > best_cost[node]: continue

    for neighbor in graph.neighbors(node):
      edge_step = edge_cost(graph, node, neighbor)
      new_cost = cost + edge_step
      if new_cost < best_cost.get(neighbor, inf):
        best_cost[neighbor] = new_cost
        frontier.push(cost=new_cost, node=neighbor, path=path + [neighbor])

  return None  # no reachable target
```

If `uniform_cost_search` returns nothing (meaning the frontier emptied without ever touching a destination), the high-level planner surfaces this as an error so the UI can tell the user that no valid tour exists for the supplied inputs.

### Stitching the Output

The final `stitch_path` step translates the node sequence into real-world coordinates. For each adjacent pair of nodes, it extracts the true road geometry of the edge, and concatenates the sampled points into one continuous LineString that can be rendered or exported.

```
function stitch_path(graph, node_path):
  if node_path is empty: return []
  coords = [lonlat(graph, node_path[0])]
  for (u, v) in pairwise(node_path):
    segment = edge_geometry_coords(graph, u, v)
    coords.extend(segment[1:])
  return coords
```

### Manual Testing

The following helper scripts are provided for development and experimentation:

#### `scripts/test_planner.py`

- **Purpose**: Quickly try the route planner from the command line using a GeoJSON file of point features (start + destinations).
- **Usage**:

  ```sh
  python -m scripts.test_planner
  ```

  Plot points in [geojson.io](https://geojson.io/) then copy the generated GeoJSON. The script will tell you where to paste your GeoJSON and will print a resulting route as GeoJSON to standard output. Afterwards, you can paste the generated GeoJSON back to [geojson.io](https://geojson.io/).

#### `scripts/togpkg_osmnx_graph.py`

- **Purpose**: Convert the default OSMnx GraphML file in `assets/` into a GeoPackage (`.gpkg`) file for use in GIS tools or other applications.
- **Usage**:

  ```sh
  python -m scripts.togpkg_osmnx_graph
  ```

  This reads `assets/ilocos_norte_osmnx.graphml` and writes `assets/ilocos_norte_osmnx.gpkg`.
