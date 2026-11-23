"""
flight_path_finder.py
====================================
Finds shortest flight routes between airports around the world and compares
how much work Dijkstra's algorithm and A* search do on a real network.

Airports are the vertices of a weighted, directed graph and airline routes are
the edges. Edge weights are great-circle distances in kilometers computed with
the haversine formula. The same formula is used as the A* heuristic, since the
straight-line distance over the Earth's surface can never be longer than any
real route.

The graph, binary heap, priority queue and Dijkstra code follow the designs in
*Problem Solving with Algorithms and Data Structures using Python* by Miller
and Ranum (https://runestone.academy/ns/books/published/pythonds/index.html):
the ``Vertex`` and ``Graph`` classes from section 8.6, the binary heap from
section 7.10, and Dijkstra's algorithm from section 8.20.

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


# ---------------------------------------------------------------------------
# Graph ADT (book section 8.6), with the extra vertex fields from section 8.9
# ---------------------------------------------------------------------------

class Vertex:
    """
    A vertex in an adjacency-list graph (book section 8.6, Listing 1).

    Besides the book's ``id`` and ``connectedTo``, each vertex has the
    ``dist``, ``pred`` and ``color`` fields that the book's extended Vertex
    uses for breadth first search and Dijkstra's algorithm (sections 8.9 and
    8.20), and an optional ``data`` field to hold airport information.

    Parameters
    ----------
    key : hashable
        Identifier for the vertex, for example an airport code
    data : object, optional
        Extra information to store with the vertex

    Attributes
    ----------
    id : hashable
        Identifier for the vertex
    connectedTo : dict
        Maps each neighboring Vertex to the weight of the edge to it
    dist : float
        Distance from the start vertex found by the last search
    pred : Vertex or None
        Previous vertex on the best path found by the last search
    color : str
        ``'white'``, ``'gray'`` or ``'black'``, used by breadth first search
    data : object
        Extra information stored with the vertex

    Examples
    --------
    >>> a, b = Vertex('A'), Vertex('B')
    >>> a.addNeighbor(b, 7)
    >>> [v.getId() for v in a.getConnections()], a.getWeight(b)
    (['B'], 7)
    """

    def __init__(self, key, data=None):
        """
        Initialize a vertex with no neighbors.

        Parameters
        ----------
        key : hashable
            Identifier for the vertex
        data : object, optional
            Extra information to store with the vertex
        """
        self.id = key
        self.connectedTo = {}
        self.data = data
        self.dist = sys.maxsize
        self.pred = None
        self.color = 'white'

    def addNeighbor(self, nbr, weight=0):
        """
        Add a directed edge from this vertex to ``nbr``.

        Parameters
        ----------
        nbr : Vertex
            Vertex the edge goes to
        weight : float, optional
            Weight of the edge

        Returns
        -------
        None
        """
        self.connectedTo[nbr] = weight

    def __str__(self):
        """
        Text showing the vertex and its neighbors.

        Returns
        -------
        str
            For example ``'A connectedTo: ['B']'``
        """
        return str(self.id) + ' connectedTo: ' + str([x.id for x in self.connectedTo])

    def getConnections(self):
        """
        Vertices this vertex has an edge to.

        Returns
        -------
        dict_keys
            The neighboring Vertex objects
        """
        return self.connectedTo.keys()

    def getId(self):
        """
        Identifier of this vertex.

        Returns
        -------
        hashable
            The key the vertex was created with
        """
        return self.id

    def getWeight(self, nbr):
        """
        Weight of the edge from this vertex to ``nbr``.

        Parameters
        ----------
        nbr : Vertex
            A neighboring vertex

        Returns
        -------
        float
            Weight of the edge
        """
        return self.connectedTo[nbr]

    def setDistance(self, d):
        """
        Set the distance from the start vertex.

        Parameters
        ----------
        d : float
            New distance

        Returns
        -------
        None
        """
        self.dist = d

    def getDistance(self):
        """
        Distance from the start vertex.

        Returns
        -------
        float
            Distance found by the last search, or ``sys.maxsize`` if the
            vertex was not reached
        """
        return self.dist

    def setPred(self, p):
        """
        Set the previous vertex on the best path.

        Parameters
        ----------
        p : Vertex or None
            Predecessor vertex

        Returns
        -------
        None
        """
        self.pred = p

    def getPred(self):
        """
        Previous vertex on the best path.

        Returns
        -------
        Vertex or None
            Predecessor vertex, or None for the start vertex
        """
        return self.pred

    def setColor(self, color):
        """
        Set the search color.

        Parameters
        ----------
        color : str
            ``'white'``, ``'gray'`` or ``'black'``

        Returns
        -------
        None
        """
        self.color = color

    def getColor(self):
        """
        Search color of the vertex.

        Returns
        -------
        str
            ``'white'``, ``'gray'`` or ``'black'``
        """
        return self.color


class Graph:
    """
    Adjacency-list graph (book section 8.6, Listing 2).

    Parameters
    ----------
    None

    Attributes
    ----------
    vertList : dict
        Maps each vertex key to its Vertex object
    numVertices : int
        Number of vertices in the graph

    Examples
    --------
    >>> g = Graph()
    >>> g.addEdge(0, 1, 5)
    >>> g.addEdge(0, 5, 2)
    >>> g.numVertices, sorted(g.getVertices())
    (3, [0, 1, 5])
    >>> 1 in g, 7 in g
    (True, False)
    """

    def __init__(self):
        """
        Initialize an empty graph.
        """
        self.vertList = {}
        self.numVertices = 0

    def addVertex(self, key, data=None):
        """
        Add a vertex to the graph.

        Parameters
        ----------
        key : hashable
            Identifier for the new vertex
        data : object, optional
            Extra information to store with the vertex

        Returns
        -------
        Vertex
            The new vertex
        """
        self.numVertices = self.numVertices + 1
        newVertex = Vertex(key, data)
        self.vertList[key] = newVertex
        return newVertex

    def getVertex(self, n):
        """
        Look up a vertex by key.

        Parameters
        ----------
        n : hashable
            Key of the vertex

        Returns
        -------
        Vertex or None
            The vertex, or None if it is not in the graph
        """
        if n in self.vertList:
            return self.vertList[n]
        else:
            return None

    def __contains__(self, n):
        """
        Support ``key in graph``.

        Parameters
        ----------
        n : hashable
            Key of a vertex

        Returns
        -------
        bool
            True if the graph has a vertex with that key
        """
        return n in self.vertList

    def addEdge(self, f, t, weight=0):
        """
        Add a directed edge, creating either vertex if needed.

        Parameters
        ----------
        f : hashable
            Key of the vertex the edge starts at
        t : hashable
            Key of the vertex the edge ends at
        weight : float, optional
            Weight of the edge

        Returns
        -------
        None
        """
        if f not in self.vertList:
            self.addVertex(f)
        if t not in self.vertList:
            self.addVertex(t)
        self.vertList[f].addNeighbor(self.vertList[t], weight)

    def getVertices(self):
        """
        Keys of all vertices in the graph.

        Returns
        -------
        dict_keys
            The vertex keys
        """
        return self.vertList.keys()

    def __iter__(self):
        """
        Iterate over the Vertex objects in the graph.

        Returns
        -------
        iterator
            Iterator over the Vertex objects
        """
        return iter(self.vertList.values())


# ---------------------------------------------------------------------------
# Binary heap and priority queue (book section 7.10, and the PriorityQueue
# with decreaseKey described in section 8.20)
# ---------------------------------------------------------------------------

class PriorityQueue:
    """
    Min priority queue of ``(priority, vertex)`` pairs with ``decreaseKey``.

    This is the binary heap from book section 7.10 (``heapList`` with an
    unused 0 at index 0, ``percUp``, ``percDown``, ``minChild``,
    ``buildHeap``, ``delMin``), changed as section 8.20 describes for
    Dijkstra's algorithm: it stores ``(priority, vertex)`` tuples, compares
    only the priorities, and adds ``decreaseKey``.

    The book does not print ``decreaseKey``. To find a vertex's place in the
    heap quickly, this version also keeps a ``position`` dictionary that is
    updated on every swap, so ``decreaseKey`` runs in O(log n) instead of
    searching the whole list.

    Parameters
    ----------
    None

    Attributes
    ----------
    heapList : list
        The heap. Index 0 holds an unused placeholder.
    currentSize : int
        Number of items in the heap
    position : dict
        Maps each vertex to its index in ``heapList``

    Examples
    --------
    >>> pq = PriorityQueue()
    >>> pq.buildHeap([(9, 'a'), (6, 'b'), (5, 'c'), (2, 'd'), (3, 'e')])
    >>> pq.decreaseKey('a', 1)
    >>> [pq.delMin() for _ in range(5)]
    ['a', 'd', 'e', 'c', 'b']
    >>> pq.isEmpty()
    True
    """

    def __init__(self):
        """
        Initialize an empty priority queue.
        """
        self.heapList = [(0, None)]
        self.currentSize = 0
        self.position = {}

    def _swap(self, i, j):
        """
        Swap two heap entries and update their positions.

        Parameters
        ----------
        i : int
            Index of the first entry
        j : int
            Index of the second entry

        Returns
        -------
        None
        """
        self.heapList[i], self.heapList[j] = self.heapList[j], self.heapList[i]
        self.position[self.heapList[i][1]] = i
        self.position[self.heapList[j][1]] = j

    def buildHeap(self, alist):
        """
        Build the heap from a list of ``(priority, vertex)`` pairs in O(n).

        Parameters
        ----------
        alist : list of tuple
            ``(priority, vertex)`` pairs

        Returns
        -------
        None
        """
        self.currentSize = len(alist)
        self.heapList = [(0, None)] + alist[:]
        self.position = {item[1]: idx for idx, item in enumerate(self.heapList) if idx > 0}
        i = len(alist) // 2
        while i > 0:
            self.percDown(i)
            i = i - 1

    def percDown(self, i):
        """
        Move the entry at index ``i`` down until the heap order holds.

        Parameters
        ----------
        i : int
            Index of the entry to move

        Returns
        -------
        None
        """
        while (i * 2) <= self.currentSize:
            mc = self.minChild(i)
            if self.heapList[i][0] > self.heapList[mc][0]:
                self._swap(i, mc)
            i = mc

    def minChild(self, i):
        """
        Index of the child of ``i`` with the smaller priority.

        Parameters
        ----------
        i : int
            Index of a parent entry

        Returns
        -------
        int
            Index of the smaller child
        """
        if i * 2 + 1 > self.currentSize:
            return i * 2
        else:
            if self.heapList[i * 2][0] < self.heapList[i * 2 + 1][0]:
                return i * 2
            else:
                return i * 2 + 1

    def percUp(self, i):
        """
        Move the entry at index ``i`` up until the heap order holds.

        Parameters
        ----------
        i : int
            Index of the entry to move

        Returns
        -------
        None
        """
        while i // 2 > 0:
            if self.heapList[i][0] < self.heapList[i // 2][0]:
                self._swap(i, i // 2)
            i = i // 2

    def add(self, k):
        """
        Insert a ``(priority, vertex)`` pair.

        Parameters
        ----------
        k : tuple
            ``(priority, vertex)`` pair

        Returns
        -------
        None
        """
        self.heapList.append(k)
        self.currentSize = self.currentSize + 1
        self.position[k[1]] = self.currentSize
        self.percUp(self.currentSize)

    def delMin(self):
        """
        Remove and return the vertex with the smallest priority.

        Returns
        -------
        object
            The vertex part of the smallest ``(priority, vertex)`` pair
        """
        retval = self.heapList[1][1]
        self._swap(1, self.currentSize)
        self.currentSize = self.currentSize - 1
        self.heapList.pop()
        del self.position[retval]
        self.percDown(1)
        return retval

    def isEmpty(self):
        """
        Whether the queue is empty.

        Returns
        -------
        bool
            True if there are no items left
        """
        return self.currentSize == 0

    def decreaseKey(self, val, amt):
        """
        Lower the priority of a vertex already in the queue.

        Parameters
        ----------
        val : object
            The vertex whose priority changes
        amt : float
            Its new, smaller priority

        Returns
        -------
        None
        """
        i = self.position[val]
        self.heapList[i] = (amt, val)
        self.percUp(i)

    def __contains__(self, vtx):
        """
        Support ``vertex in queue``.

        Parameters
        ----------
        vtx : object
            A vertex

        Returns
        -------
        bool
            True if the vertex is still in the queue
        """
        return vtx in self.position


# ---------------------------------------------------------------------------
# Search results and algorithms
# ---------------------------------------------------------------------------

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
        Number of vertices removed from the priority queue with ``delMin``
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


def dijkstra(aGraph, start, end=None):
    """
    Dijkstra's shortest-path algorithm (book section 8.20, Listing 1).

    Every vertex starts with distance ``sys.maxsize`` and is put into the
    priority queue with ``buildHeap``. Each step removes the closest vertex
    with ``delMin`` and relaxes its edges, lowering a neighbor's distance
    with ``setDistance``, ``setPred`` and ``decreaseKey`` when a shorter
    path is found.

    Two small additions to the book's version: distances, predecessors and
    colors are reset first so the graph can be searched many times, and if
    ``end`` is given the search stops once ``end`` is removed from the
    queue, because its distance is final at that point.

    Parameters
    ----------
    aGraph : Graph
        Graph to search. Edge weights must not be negative.
    start : Vertex
        Vertex to start from
    end : Vertex, optional
        Stop early once this vertex's distance is final

    Returns
    -------
    int
        Number of vertices removed from the priority queue (expanded)

    Examples
    --------
    >>> g = Graph()
    >>> for f, t, w in [('u', 'v', 2), ('u', 'w', 5), ('u', 'x', 1), ('x', 'w', 3),
    ...                 ('x', 'y', 1), ('y', 'w', 1), ('y', 'z', 1), ('w', 'z', 5)]:
    ...     g.addEdge(f, t, w)
    >>> expanded = dijkstra(g, g.getVertex('u'))
    >>> {v.getId(): v.getDistance() for v in g}
    {'u': 0, 'v': 2, 'w': 3, 'x': 1, 'y': 2, 'z': 3}
    >>> [v.getId() for v in traverse(g.getVertex('z'))]
    ['u', 'x', 'y', 'z']
    """
    for v in aGraph:
        v.setDistance(sys.maxsize)
        v.setPred(None)
        v.setColor('white')

    pq = PriorityQueue()
    start.setDistance(0)
    pq.buildHeap([(v.getDistance(), v) for v in aGraph])
    expanded = 0
    while not pq.isEmpty():
        currentVert = pq.delMin()
        if currentVert.getDistance() == sys.maxsize:
            break  # everything left in the queue is unreachable
        expanded += 1
        currentVert.setColor('black')
        if currentVert is end:
            break
        for nextVert in currentVert.getConnections():
            newDist = currentVert.getDistance() + currentVert.getWeight(nextVert)
            if newDist < nextVert.getDistance():
                nextVert.setDistance(newDist)
                nextVert.setPred(currentVert)
                pq.decreaseKey(nextVert, newDist)
    return expanded


def traverse(y):
    """
    Follow predecessor links back to the start (book section 8.9, Listing 3).

    The book's version prints each vertex; this one returns them in order
    from the start vertex to ``y``.

    Parameters
    ----------
    y : Vertex
        Last vertex of the path

    Returns
    -------
    list of Vertex
        Vertices from the start of the search to ``y``
    """
    path = [y]
    x = y
    while x.getPred():
        x = x.getPred()
        path.append(x)
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Flight network
# ---------------------------------------------------------------------------

@dataclass
class Airport:
    """
    Information stored in each airport vertex's ``data`` field.

    Parameters
    ----------
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
    """
    name: str
    city: str
    country: str
    lat: float
    lon: float


class FlightGraph(Graph):
    """
    Graph of airports (vertices) and nonstop routes (edges).

    Vertex keys are IATA airport codes, each vertex's ``data`` is an
    :class:`Airport`, and edge weights are great-circle distances in km.

    Parameters
    ----------
    None

    Attributes
    ----------
    vertList : dict
        Maps each airport code to its Vertex
    numVertices : int
        Number of airports in the graph

    Examples
    --------
    >>> g = FlightGraph()
    >>> g.addAirport('JFK', 'John F Kennedy Intl', 'New York', 'United States', 40.6413, -73.7781)
    >>> g.addAirport('LHR', 'Heathrow', 'London', 'United Kingdom', 51.4700, -0.4543)
    >>> g.addRoute('JFK', 'LHR')
    >>> jfk, lhr = g.getVertex('JFK'), g.getVertex('LHR')
    >>> round(jfk.getWeight(lhr))
    5540
    """

    def addAirport(self, code, name, city, country, lat, lon):
        """
        Add an airport vertex.

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
        self.addVertex(code, Airport(name, city, country, lat, lon))

    def addRoute(self, src, dst):
        """
        Add a directed route weighted by great-circle distance.

        Both airports must already have been added with
        :meth:`addAirport`. Adding the same route twice (for example,
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
        a = self.vertList[src].data
        b = self.vertList[dst].data
        self.addEdge(src, dst, haversine(a.lat, a.lon, b.lat, b.lon))

    def numRoutes(self):
        """
        Number of routes (edges) in the graph.

        Returns
        -------
        int
            Count of directed routes
        """
        return sum(len(v.connectedTo) for v in self)

    def loadAirports(self, path):
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
                self.addAirport(code, row[1], row[2], row[3], float(row[6]), float(row[7]))
                added += 1
        return added

    def loadRoutes(self, path):
        """
        Load routes from an OpenFlights ``routes.dat`` file.

        Only nonstop routes (0 stops) between airports already in the graph
        are added. Call :meth:`loadAirports` first.

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
                if stops != '0' or src == dst or src not in self or dst not in self:
                    continue
                self.addRoute(src, dst)
                used += 1
        return used

    def removeUnservedAirports(self):
        """
        Remove airports that have no routes in or out.

        Many airports in the OpenFlights list (small airfields, closed
        airports) have no scheduled routes. They can never be part of a
        route, so removing them makes the graph smaller.

        Returns
        -------
        int
            Number of airports removed

        Examples
        --------
        >>> g = FlightGraph()
        >>> for code in 'ABC':
        ...     g.addAirport(code, code, code, 'X', 0, 0)
        >>> g.addRoute('A', 'B')
        >>> g.removeUnservedAirports()
        1
        >>> sorted(g.getVertices()), g.numVertices
        (['A', 'B'], 2)
        """
        served = {nbr for v in self for nbr in v.getConnections()}
        served.update(v for v in self if v.connectedTo)
        unserved = [v.getId() for v in self if v not in served]
        for code in unserved:
            del self.vertList[code]
        self.numVertices = len(self.vertList)
        return len(unserved)

    @classmethod
    def fromOpenFlights(cls, data_dir=DEFAULT_DATA_DIR):
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
        graph.loadAirports(airports_path)
        graph.loadRoutes(routes_path)
        graph.removeUnservedAirports()
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
        a = self.vertList[code].data
        return f'{code}  {a.name} ({a.city}, {a.country})'

    def shortestRoute(self, src, dst):
        """
        Shortest route by distance between two airports, using
        :func:`dijkstra`.

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
        ...     g.addAirport(code, code, code, 'X', lat, lon)
        >>> for s, d in [('A', 'B'), ('B', 'C'), ('A', 'D'), ('D', 'C')]:
        ...     g.addRoute(s, d)
        >>> g.shortestRoute('A', 'C').path
        ['A', 'B', 'C']
        >>> g.shortestRoute('C', 'A').found
        False
        """
        for code in (src, dst):
            if code not in self:
                raise KeyError(f'Unknown airport: {code}')
        start, end = self.getVertex(src), self.getVertex(dst)

        t0 = time.perf_counter()
        expanded = dijkstra(self, start, end)
        result = RouteResult('Dijkstra', nodes_expanded=expanded,
                             seconds=time.perf_counter() - t0)
        if end.getDistance() != sys.maxsize:
            result.path = [v.getId() for v in traverse(end)]
            result.distance_km = end.getDistance()
        return result


def format_route(graph, result):
    """
    Format a route as a text itinerary.

    Parameters
    ----------
    graph : FlightGraph
        Graph the route was found in
    result : RouteResult
        Result returned by a search such as :meth:`FlightGraph.shortestRoute`

    Returns
    -------
    str
        Multi-line itinerary listing each airport, each leg's distance,
        and a summary line

    Examples
    --------
    >>> g = FlightGraph()
    >>> g.addAirport('JFK', 'John F Kennedy Intl', 'New York', 'United States', 40.6413, -73.7781)
    >>> g.addAirport('LHR', 'Heathrow', 'London', 'United Kingdom', 51.4700, -0.4543)
    >>> g.addRoute('JFK', 'LHR')
    >>> print(format_route(g, g.shortestRoute('JFK', 'LHR')))  # doctest: +ELLIPSIS
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
            leg = graph.getVertex(code).getWeight(graph.getVertex(result.path[i + 1]))
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

    graph = FlightGraph.fromOpenFlights(args.data_dir)
    print(f'Loaded {graph.numVertices:,} airports and {graph.numRoutes():,} routes\n')

    if args.src:
        pairs = [(args.src.upper(), args.dst.upper())]
    else:
        pairs = DEMO_ROUTES

    for src, dst in pairs:
        try:
            print(format_route(graph, graph.shortestRoute(src, dst)))
        except KeyError as err:
            print(f'Error: {err.args[0]}')
        print()


if __name__ == '__main__':
    main()
