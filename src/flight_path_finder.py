"""
flight_path_finder.py
====================================
Finds shortest flight routes between airports around the world and compares
how much work Dijkstra's algorithm and A* search do on a real network.

Airports are the nodes of a weighted, directed graph and airline routes are
the edges. Edge weights are great-circle distances in kilometers computed with
the haversine formula. The same formula is used as the A* heuristic, since the
straight-line distance over the Earth's surface can never be longer than any
real route.

Data comes from the OpenFlights airports and routes datasets
(https://openflights.org/data.html). The files are downloaded automatically
into a ``data`` folder the first time the program runs.

Run from the command line::

    python src/flight_path_finder.py JFK SIN
    python src/flight_path_finder.py          # runs a few demo routes

| Author: Ruben Sanchez Gutierrez
| Date: 2026 November 23
"""

import argparse
import csv
import heapq
import math
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, field

EARTH_RADIUS_KM = 6371.0
"""float: Mean radius of the Earth in kilometers."""

OPENFLIGHTS_URL = 'https://raw.githubusercontent.com/jpatokal/openflights/master/data/'
"""str: Base URL the OpenFlights data files are downloaded from."""

DATA_FILES = ('airports.dat', 'routes.dat')
"""tuple of str: OpenFlights files the program needs."""

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
"""str: Folder the data files are stored in (``data/`` at the repository root)."""

DEMO_ROUTES = [('JFK', 'SIN'), ('LAX', 'SYD'), ('DTW', 'NRT'), ('MAD', 'HNL')]
"""list of tuple: Airport pairs used when the program is run with no arguments."""


def haversine(lat1, lon1, lat2, lon2):
    """
    Great-circle distance between two points on the Earth.

    Parameters
    ----------
    lat1 : float
        Latitude of the first point in degrees
    lon1 : float
        Longitude of the first point in degrees
    lat2 : float
        Latitude of the second point in degrees
    lon2 : float
        Longitude of the second point in degrees

    Returns
    -------
    float
        Distance between the two points in kilometers

    Examples
    --------
    >>> round(haversine(40.6413, -73.7781, 51.4700, -0.4543))
    5540
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def download_data(data_dir=DEFAULT_DATA_DIR):
    """
    Download the OpenFlights data files if they are not already present.

    Parameters
    ----------
    data_dir : str, optional
        Folder to store the files in. Created if it does not exist.

    Returns
    -------
    list of str
        Paths to the downloaded (or already present) files, in the same
        order as :data:`DATA_FILES`
    """
    os.makedirs(data_dir, exist_ok=True)
    paths = []
    for name in DATA_FILES:
        path = os.path.join(data_dir, name)
        if not os.path.exists(path):
            print(f'Downloading {name} from OpenFlights...')
            urllib.request.urlretrieve(OPENFLIGHTS_URL + name, path)
        paths.append(path)
    return paths


@dataclass
class RouteResult:
    """
    Result of a shortest-path search.

    Parameters
    ----------
    algorithm : str
        Name of the algorithm that produced the result
    path : list of str
        Airport codes from source to destination. Empty if no route exists.
    distance_km : float
        Total length of the route in kilometers (``math.inf`` if no route)
    nodes_expanded : int
        Number of airports removed from the priority queue and finalized
    seconds : float
        Wall-clock time the search took
    """
    algorithm: str
    path: list = field(default_factory=list)
    distance_km: float = math.inf
    nodes_expanded: int = 0
    seconds: float = 0.0

    @property
    def legs(self):
        """
        Number of flights in the route.

        Returns
        -------
        int
            ``len(path) - 1``, or 0 if there is no route
        """
        return max(len(self.path) - 1, 0)

    @property
    def found(self):
        """
        Whether a route was found.

        Returns
        -------
        bool
            True if the path is not empty
        """
        return bool(self.path)


class FlightGraph:
    """
    Weighted, directed graph of airports and the routes between them.

    Parameters
    ----------
    None

    Attributes
    ----------
    airports : dict
        Maps an airport code (str) to a tuple of
        ``(name, city, country, latitude, longitude)``
    adjacency : dict
        Maps an airport code (str) to a dict of
        ``{destination code: distance in km}``

    Examples
    --------
    >>> g = FlightGraph()
    >>> g.add_airport('JFK', 'John F Kennedy Intl', 'New York', 'United States', 40.6413, -73.7781)
    >>> g.add_airport('LHR', 'Heathrow', 'London', 'United Kingdom', 51.4700, -0.4543)
    >>> g.add_route('JFK', 'LHR')
    >>> round(g.adjacency['JFK']['LHR'])
    5540
    """

    def __init__(self):
        """
        Initialize an empty FlightGraph.
        """
        self.airports = {}
        self.adjacency = {}

    def add_airport(self, code, name, city, country, lat, lon):
        """
        Add an airport (node) to the graph.

        Parameters
        ----------
        code : str
            IATA airport code, for example ``'JFK'``
        name : str
            Full airport name
        city : str
            City the airport serves
        country : str
            Country the airport is in
        lat : float
            Latitude in degrees
        lon : float
            Longitude in degrees

        Returns
        -------
        None
        """
        self.airports[code] = (name, city, country, lat, lon)
        self.adjacency.setdefault(code, {})

    def add_route(self, src, dst):
        """
        Add a directed route (edge) weighted by great-circle distance.

        Both airports must already have been added with
        :meth:`add_airport`. Adding the same route twice (for example,
        flown by two airlines) keeps a single edge.

        Parameters
        ----------
        src : str
            Code of the departure airport
        dst : str
            Code of the arrival airport

        Returns
        -------
        None

        Raises
        ------
        KeyError
            If either airport is not in the graph
        """
        _, _, _, lat1, lon1 = self.airports[src]
        _, _, _, lat2, lon2 = self.airports[dst]
        self.adjacency[src][dst] = haversine(lat1, lon1, lat2, lon2)

    def num_airports(self):
        """
        Number of airports (nodes) in the graph.

        Returns
        -------
        int
            Count of airports
        """
        return len(self.airports)

    def num_routes(self):
        """
        Number of routes (edges) in the graph.

        Returns
        -------
        int
            Count of directed routes
        """
        return sum(len(dests) for dests in self.adjacency.values())

    def load_airports(self, path):
        """
        Load airports from an OpenFlights ``airports.dat`` file.

        Airports without an IATA code (``\\N`` in the file) are skipped,
        since routes refer to airports by IATA code.

        Parameters
        ----------
        path : str
            Path to ``airports.dat``

        Returns
        -------
        int
            Number of airports added
        """
        added = 0
        with open(path, encoding='utf-8') as f:
            for row in csv.reader(f):
                # Columns: id, name, city, country, IATA, ICAO, lat, lon, ...
                code = row[4]
                if len(code) != 3 or code == '\\N':
                    continue
                self.add_airport(code, row[1], row[2], row[3],
                                 float(row[6]), float(row[7]))
                added += 1
        return added

    def load_routes(self, path):
        """
        Load routes from an OpenFlights ``routes.dat`` file.

        Only nonstop routes (0 stops) between airports already in the graph
        are added. Call :meth:`load_airports` first.

        Parameters
        ----------
        path : str
            Path to ``routes.dat``

        Returns
        -------
        int
            Number of route rows used (before duplicate routes are merged)
        """
        used = 0
        with open(path, encoding='utf-8') as f:
            for row in csv.reader(f):
                # Columns: airline, airline id, src, src id, dst, dst id,
                #          codeshare, stops, equipment
                src, dst, stops = row[2], row[4], row[7]
                if stops != '0' or src not in self.airports or dst not in self.airports:
                    continue
                if src == dst:
                    continue
                self.add_route(src, dst)
                used += 1
        return used

    def remove_unserved_airports(self):
        """
        Remove airports that have no routes in or out.

        Many airports in the OpenFlights list (small airfields, closed
        airports) have no scheduled routes. They can never be part of a
        route, so removing them makes the graph smaller and its statistics
        more meaningful.

        Returns
        -------
        int
            Number of airports removed

        Examples
        --------
        >>> g = FlightGraph()
        >>> for code in 'ABC':
        ...     g.add_airport(code, code, code, 'X', 0, 0)
        >>> g.add_route('A', 'B')
        >>> g.remove_unserved_airports()
        1
        >>> sorted(g.airports)
        ['A', 'B']
        """
        served = {dst for dests in self.adjacency.values() for dst in dests}
        served.update(src for src, dests in self.adjacency.items() if dests)
        unserved = [code for code in self.airports if code not in served]
        for code in unserved:
            del self.airports[code]
            del self.adjacency[code]
        return len(unserved)

    @classmethod
    def from_openflights(cls, data_dir=DEFAULT_DATA_DIR):
        """
        Build a graph from the OpenFlights data, downloading it if needed.

        Parameters
        ----------
        data_dir : str, optional
            Folder that holds (or will hold) ``airports.dat`` and
            ``routes.dat``

        Returns
        -------
        FlightGraph
            Graph of every nonstop route and every airport that has at
            least one route
        """
        airports_path, routes_path = download_data(data_dir)
        graph = cls()
        graph.load_airports(airports_path)
        graph.load_routes(routes_path)
        graph.remove_unserved_airports()
        return graph

    def describe(self, code):
        """
        Human-readable description of an airport.

        Parameters
        ----------
        code : str
            IATA airport code

        Returns
        -------
        str
            For example ``'JFK  John F Kennedy International Airport
            (New York, United States)'``
        """
        name, city, country, _, _ = self.airports[code]
        return f'{code}  {name} ({city}, {country})'

    def dijkstra(self, src, dst):
        """
        Shortest route by distance using Dijkstra's algorithm.

        Uses a binary heap (:mod:`heapq`) as the priority queue with lazy
        deletion: when a shorter distance to an airport is found, a new
        entry is pushed and stale entries are skipped when popped. The
        search stops as soon as the destination is popped, because its
        distance is final at that point.

        Parameters
        ----------
        src : str
            Code of the departure airport
        dst : str
            Code of the arrival airport

        Returns
        -------
        RouteResult
            The route, its length, and how many airports were expanded.
            ``result.path`` is empty if ``dst`` cannot be reached.

        Raises
        ------
        KeyError
            If either airport is not in the graph

        Examples
        --------
        >>> g = FlightGraph()
        >>> for code, lat, lon in [('A', 0, 0), ('B', 0, 10), ('C', 0, 20), ('D', 30, 10)]:
        ...     g.add_airport(code, code, code, 'X', lat, lon)
        >>> for s, d in [('A', 'B'), ('B', 'C'), ('A', 'D'), ('D', 'C')]:
        ...     g.add_route(s, d)
        >>> g.dijkstra('A', 'C').path
        ['A', 'B', 'C']
        >>> g.dijkstra('C', 'A').found
        False
        """
        if src not in self.airports:
            raise KeyError(f'Unknown airport: {src}')
        if dst not in self.airports:
            raise KeyError(f'Unknown airport: {dst}')

        start = time.perf_counter()
        dist = {src: 0.0}
        prev = {}
        done = set()
        heap = [(0.0, src)]
        expanded = 0

        while heap:
            d, node = heapq.heappop(heap)
            if node in done:
                continue  # stale entry left behind by lazy deletion
            done.add(node)
            expanded += 1
            if node == dst:
                break
            for nbr, weight in self.adjacency[node].items():
                new_d = d + weight
                if new_d < dist.get(nbr, math.inf):
                    dist[nbr] = new_d
                    prev[nbr] = node
                    heapq.heappush(heap, (new_d, nbr))

        result = RouteResult('Dijkstra', nodes_expanded=expanded,
                             seconds=time.perf_counter() - start)
        if dst in done:
            result.path = _rebuild_path(prev, src, dst)
            result.distance_km = dist[dst]
        return result


def _rebuild_path(prev, src, dst):
    """
    Follow predecessor links back from ``dst`` to ``src``.

    Parameters
    ----------
    prev : dict
        Maps each airport code to the airport it was reached from
    src : str
        Code of the departure airport
    dst : str
        Code of the arrival airport

    Returns
    -------
    list of str
        Airport codes from ``src`` to ``dst``
    """
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def format_route(graph, result):
    """
    Format a route as a text itinerary.

    Parameters
    ----------
    graph : FlightGraph
        Graph the route was found in
    result : RouteResult
        Result returned by a search such as :meth:`FlightGraph.dijkstra`

    Returns
    -------
    str
        Multi-line itinerary listing each airport, each leg's distance,
        and a summary line

    Examples
    --------
    >>> g = FlightGraph()
    >>> g.add_airport('JFK', 'John F Kennedy Intl', 'New York', 'United States', 40.6413, -73.7781)
    >>> g.add_airport('LHR', 'Heathrow', 'London', 'United Kingdom', 51.4700, -0.4543)
    >>> g.add_route('JFK', 'LHR')
    >>> print(format_route(g, g.dijkstra('JFK', 'LHR')))  # doctest: +ELLIPSIS
    Dijkstra: JFK -> LHR
      JFK  John F Kennedy Intl (New York, United States)
         |  5,540 km
      LHR  Heathrow (London, United Kingdom)
      Total: 5,540 km | 1 leg | airports expanded: 2 | ... ms
    """
    if not result.found:
        return f'{result.algorithm}: no route found (airports expanded: {result.nodes_expanded:,})'

    lines = [f'{result.algorithm}: {result.path[0]} -> {result.path[-1]}']
    for i, code in enumerate(result.path):
        lines.append(f'  {graph.describe(code)}')
        if i < len(result.path) - 1:
            leg = graph.adjacency[code][result.path[i + 1]]
            lines.append(f'     |  {leg:,.0f} km')
    leg_word = 'leg' if result.legs == 1 else 'legs'
    lines.append(f'  Total: {result.distance_km:,.0f} km | {result.legs} {leg_word} | '
                 f'airports expanded: {result.nodes_expanded:,} | '
                 f'{result.seconds * 1000:.1f} ms')
    return '\n'.join(lines)


def main():
    """
    Command-line entry point.

    With two airport codes, prints the Dijkstra route between them.
    With no arguments, prints a few demo routes from :data:`DEMO_ROUTES`.

    Returns
    -------
    None
    """
    parser = argparse.ArgumentParser(description='Find the shortest flight route between two airports.')
    parser.add_argument('src', nargs='?', help='departure airport IATA code, e.g. JFK')
    parser.add_argument('dst', nargs='?', help='arrival airport IATA code, e.g. SIN')
    parser.add_argument('--data-dir', default=DEFAULT_DATA_DIR, help='folder for the OpenFlights files')
    args = parser.parse_args()
    if bool(args.src) != bool(args.dst):
        parser.error('give both a departure and an arrival airport, or neither')

    # Airport names contain accents (e.g. Madrid-Barajas); print them correctly
    # even when the Windows console defaults to a non-UTF-8 code page.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    graph = FlightGraph.from_openflights(args.data_dir)
    print(f'Loaded {graph.num_airports():,} airports and {graph.num_routes():,} routes\n')

    if args.src:
        pairs = [(args.src.upper(), args.dst.upper())]
    else:
        pairs = DEMO_ROUTES

    for src, dst in pairs:
        try:
            print(format_route(graph, graph.dijkstra(src, dst)))
        except KeyError as err:
            print(f'Error: {err.args[0]}')
        print()


if __name__ == '__main__':
    main()
