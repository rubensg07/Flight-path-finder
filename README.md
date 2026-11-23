# ✈️ Flight Path Finder

[![Docs](https://github.com/rubensg07/Flight-path-finder/actions/workflows/docs.yml/badge.svg)](https://github.com/rubensg07/Flight-path-finder/actions/workflows/docs.yml)

**📖 Documentation:** https://rubensg07.github.io/Flight-path-finder/

Flight Path Finder models the world's airline network as a graph and finds the
shortest route between any two airports. It compares **Dijkstra's algorithm**
with **A\* search** to show how much less work A\* does when it is guided by a
good heuristic.

> CSCI 310 (Data Structures & Algorithms) final project by Ruben Sanchez Gutierrez.

## The problem

- **Nodes:** 3,257 airports that have at least one scheduled route
- **Edges:** 37,041 directed nonstop routes (routes flown by several airlines count once)
- **Weights:** great-circle distance in km, computed with the haversine formula

Both algorithms find the same shortest route. A\* uses the straight-line
distance to the destination as a heuristic. That distance can never be longer
than any real route, so A\* still finds the optimal path while exploring far
fewer airports. BFS is also used to find the route with the fewest layovers.

## Example output

```
$ python src/flight_path_finder.py MAD HNL
Loaded 3,257 airports and 37,041 routes

Dijkstra: MAD -> HNL
  MAD  Adolfo Suárez Madrid–Barajas Airport (Madrid, Spain)
     |  1,215 km
  BRS  Bristol Airport (Bristol, United Kingdom)
     |  1,817 km
  KEF  Keflavik International Airport (Keflavik, Iceland)
     |  4,922 km
  YEG  Edmonton International Airport (Edmonton, Canada)
     |  809 km
  YVR  Vancouver International Airport (Vancouver, Canada)
     |  4,354 km
  HNL  Daniel K Inouye International Airport (Honolulu, United States)
  Total: 13,117 km | 5 legs | airports expanded: 2,896 | 51.8 ms
```

Dijkstra minimizes total distance only, so it happily takes 5 legs to save a
few hundred kilometers. The BFS "fewest layovers" search (coming next) will
show the trade-off. Next, A\* will be compared on the same routes by the
number of airports expanded, and routes will be drawn on a world map.

## Data

[OpenFlights](https://openflights.org/data.html): `airports.dat` and `routes.dat`.
The files are downloaded automatically into `data/` the first time the
program runs. The route data dates from 2014, so some routes no longer exist.

## Tech stack

| Purpose        | Library                         |
| -------------- | ------------------------------- |
| Data loading   | Python `csv`, `urllib`          |
| Graph & search | `Vertex`, `Graph`, `PriorityQueue` and `dijkstra` written from scratch following [Problem Solving with Algorithms and Data Structures using Python](https://runestone.academy/ns/books/published/pythonds/index.html) (sections 7.10, 8.6, 8.20) |
| Verification   | `networkx`                      |
| Maps           | `matplotlib` / `plotly`         |
| Documentation  | Sphinx, published to GitHub Pages |

## Getting started

```bash
uv venv .venv --python 3.12
source .venv/Scripts/activate   # Windows Git Bash; use .venv\Scripts\activate in PowerShell
uv pip install sphinx
python src/flight_path_finder.py           # demo routes
python src/flight_path_finder.py JFK SIN   # any two IATA airport codes
```

Build the docs locally:

```bash
cd docs
sphinx-build -M html . _build
```

## Roadmap

- [x] Project setup, Sphinx docs, automatic GitHub Pages deployment
- [x] **Progress report 1:** load OpenFlights data into the graph, Dijkstra, text output
- [ ] **Progress report 2:** A\* and BFS, comparison over 100 random airport pairs, first map
- [ ] **Final:** polished maps, timing and nodes-expanded charts, results in this README

## How AI was used

This project used [Claude Code](https://claude.com/claude-code) (Anthropic) for:

- Brainstorming project ideas and choosing a repository name
- Setting up the Sphinx documentation and the GitHub Actions workflow that publishes it
- The starter `FlightGraph` class and `haversine` function, including their docstrings
- Progress report 1 code: OpenFlights loading, Dijkstra's algorithm, the text
  itinerary output, and the command-line interface. Dijkstra's results were
  checked against `networkx` on 300 random airport pairs (all matched).

Everything AI-generated was reviewed and tested by me. This section will be
updated as the project progresses.
