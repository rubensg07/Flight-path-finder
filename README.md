# ✈️ Flight Path Finder

[![Docs](https://github.com/rubensg07/Flight-path-finder/actions/workflows/docs.yml/badge.svg)](https://github.com/rubensg07/Flight-path-finder/actions/workflows/docs.yml)

**📖 Documentation:** https://rubensg07.github.io/Flight-path-finder/

Flight Path Finder models the world's airline network as a graph and finds the
shortest route between any two airports. It compares **Dijkstra's algorithm**
with **A\* search** to show how much less work A\* does when it is guided by a
good heuristic.

> CSCI 310 (Data Structures & Algorithms) final project by Ruben Sanchez Gutierrez.

## The problem

- **Nodes:** ~7,000 airports worldwide
- **Edges:** ~67,000 directed airline routes
- **Weights:** great-circle distance in km, computed with the haversine formula

Both algorithms find the same shortest route. A\* uses the straight-line
distance to the destination as a heuristic. That distance can never be longer
than any real route, so A\* still finds the optimal path while exploring far
fewer airports. BFS is also used to find the route with the fewest layovers.

## Example output (planned)

```
Route: JFK -> SIN
Dijkstra: 18,412 km | 3 legs | nodes expanded: 2,941
A*:       18,412 km | 3 legs | nodes expanded:   612
BFS (fewest hops): JFK -> DOH -> SIN (2 legs, 19,870 km)
```

The project will also draw each route on a world map, shading the airports
that each algorithm explored.

## Data

[OpenFlights](https://openflights.org/data.html): `airports.dat` and `routes.dat`.

## Tech stack

| Purpose        | Library                         |
| -------------- | ------------------------------- |
| Data loading   | `pandas`                        |
| Graph & search | Custom implementation, `heapq`  |
| Verification   | `networkx`                      |
| Maps           | `matplotlib` / `plotly`         |
| Documentation  | Sphinx, published to GitHub Pages |

## Getting started

```bash
uv venv .venv --python 3.12
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate in PowerShell
uv pip install sphinx
python src/flight_path_finder.py
```

Build the docs locally:

```bash
cd docs
sphinx-build -M html . _build
```

## Roadmap

- [x] Project setup, Sphinx docs, automatic GitHub Pages deployment
- [ ] **Progress report 1:** load OpenFlights data into the graph, Dijkstra, text output
- [ ] **Progress report 2:** A\* and BFS, comparison over 100 random airport pairs, first map
- [ ] **Final:** polished maps, timing and nodes-expanded charts, results in this README

## How AI was used

This project used [Claude Code](https://claude.com/claude-code) (Anthropic) for:

- Brainstorming project ideas and choosing a repository name
- Setting up the Sphinx documentation and the GitHub Actions workflow that publishes it
- The starter `FlightGraph` class and `haversine` function, including their docstrings

Everything AI-generated was reviewed and tested by me. This section will be
updated as the project progresses.
