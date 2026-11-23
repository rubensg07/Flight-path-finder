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
(https://openflights.org/data.html).

| Author: Ruben Sanchez Gutierrez
| Date: 2026 November 23
"""

import math

EARTH_RADIUS_KM = 6371.0
"""float: Mean radius of the Earth in kilometers."""


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
        :meth:`add_airport`.

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


if __name__ == '__main__':
    """Runs if file called as script as opposed to being imported as a library
    """
    g = FlightGraph()
    g.add_airport('JFK', 'John F Kennedy Intl', 'New York', 'United States', 40.6413, -73.7781)
    g.add_airport('LHR', 'Heathrow', 'London', 'United Kingdom', 51.4700, -0.4543)
    g.add_route('JFK', 'LHR')
    print(f'{g.num_airports()} airports, {g.num_routes()} routes')
    print(f"JFK -> LHR: {g.adjacency['JFK']['LHR']:,.0f} km")
