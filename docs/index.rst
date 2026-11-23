.. Flight Path Finder documentation master file, created by
   sphinx-quickstart on Mon Nov 23 12:02:09 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Flight Path Finder documentation
================================

Flight Path Finder models the world's airline network as a weighted graph
using the `OpenFlights <https://openflights.org/data.html>`_ dataset. It finds
the shortest route between any two airports and compares how many airports
Dijkstra's algorithm and A* search (with a great-circle distance heuristic)
have to explore to find it.

Source code: https://github.com/rubensg07/Flight-path-finder

.. automodule:: flight_path_finder
   :members:
   :undoc-members:
   :show-inheritance:

.. toctree::
   :maxdepth: 2
   :caption: Contents:
