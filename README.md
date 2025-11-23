# `TOUR-IN` for MMSU-CS162

App for finding the shortest path to tour places around Ilocos Norte — made with Python.

## Features

- Select multiple Points of Interest (POIs) to visit
- Start path from any starting location

## Table of Contents

1. [User Manual](#user-manual)
2. [Algorithm](#algorithm)

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

Before the app can run search algorithms, a routable graph representation of the original _OpenStreetMap_ data has to be generated first.

- Generate the routable graph from the _OpenStreetMap_ extract:
  - `python -m scripts.build_graph`
- (Optional) Export the graph back to _GeoJSON_ for validation:
  - `python -m scripts.build_graph_geojson`

The graph JSON stores `networkx` node-link data with untouched `lon`/`lat` intersections and edge coordinate chains so it can be reconstructed losslessly.

## Algorithm
