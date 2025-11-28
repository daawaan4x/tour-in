# `TOUR-IN` for MMSU-CS162

App for finding the shortest path to tour places around Ilocos Norte — made with Python.

## Features

- Select multiple Points of Interest (POIs) to visit
- Start path from any starting location

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

## Algorithm

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
