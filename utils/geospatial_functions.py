import geocoder
import json
import networkx as nx
import numpy as np
import os.path
import osmnx as ox
import re
import requests
from collections import OrderedDict
from loguru import logger


class Pathfinder:

    def __init__(self):
        self.location = None
        self.days = None
        self.route = None
        self.graph = None
        self.possible_places = None
        self.plan = None
        self.nodes = None
        self.distance_matrix = None

    def build_graph(self):
        """ Downloads map if it doesn't exist, this takes a while """
        logger.info('Checking if Istanbul graph data already exists...')
        if not os.path.isfile('istanbul.graphml'):
            file_name = "istanbul.graphml"
            logger.info('Graph data does not exist, creating Istanbul data...')
            G = ox.graph_from_place('Istanbul, Turkey', network_type='drive', which_result=2)
            ox.save_graphml(G, filepath=file_name)
            logger.info(f"Graph saved as {file_name}")

    def load_graph(self, graph_file):
        if os.path.isfile(graph_file):
            logger.info("Graph data found. Loading...")
            self.graph = ox.load_graphml(graph_file)
            logger.info("Graph loaded")
        else:
            logger.error(f"There is no graph file called {graph_file}.")

    def get_overpass_data(self, filename, url, query):
        """ Imports data from Overpass API and saves it to a JSON file """
        logger.info('Checking if Overpass data already exists...')
        if not os.path.isfile(filename):
            logger.info('Overpass data does not exist, creating...')
            response = requests.get(url, params={'data': query})
            data = response.json()
            with open(filename, 'w') as outfile:
                json.dump(data, outfile)
                logger.info(f"POI list saved to {filename}.")
        else:
            logger.info('Overpass data already exists, no need to create.')

    def get_user_location_by_name(self):
        """ Finds the location of the user by using geocoding """
        geocoded_location = None
        confirmation = False
        while(geocoded_location is None) or (not confirmation):
            location_name = input("Please enter the location where you are starting your journey in Istanbul(no need to specify Istanbul and Turkey):\n")
            location_name = location_name + ",Istanbul, Turkey"
            geocoded_location = geocoder.osm(location_name)
            if geocoded_location:
                logger.info(f"User location is {geocoded_location}")
                logger.info(f"Latitude:{geocoded_location.lat}, Longitude:{geocoded_location.lng}")
                user_confirmation = input("Is this the correct address?(y/n)")
                if user_confirmation.lower() == "y":
                    confirmation = True
            else:
                logger.error("User location could not be found. Please try again.")
        self.location = geocoded_location.json
        self.location["name"] = location_name

    def get_trip_days(self):
        """ Gets the number of days the user is staying in Istanbul """
        day_count = None
        while(day_count is None) or (day_count <= 0) or (day_count > 5):
            try:
                day_count = int(input("How many days would you like to plan?(max 5):\n"))
            except ValueError:
                logger.error("Please enter a number") 
            if day_count <= 0:
                logger.error("Please enter a valid day count.")
            if day_count > 5:
                logger.error("Please enter a day count less than 6.")

        self.days = day_count
    
    def get_possible_touristic_places(self, json_file):
        """ Gets the list of all touristic places on OpenStreet Map """
        places = []
        pattern = re.compile("[^0-9\u0621-\u064a\ufb50-\ufdff\ufe70-\ufefc]")
        with open(json_file, 'r') as f:
            logger.info(f"Reading POI List from {json_file}.")
            data = json.load(f)
            logger.info("Completed reading POI List")
        for element in data['elements']:
            if (pattern.match(element["tags"]["name"])) and (element["tags"]["name"] not in [place["tags"]["name"] for place in places]):
                places.append(element)
        self.possible_places = places

    def form_touristic_places(self):
        """ Gets the information of famous places to visit """
        priority_list = ["Yerebatan Sarnıcı",
                        "Kapali Carsi",
                        "Dolmabahçe Sarayı",
                        "Sultanahmet Camii",
                        "Istiklâl Caddesi",
                        "Galata Tower",
                        "Osmanlı Bankası Müzesi",
                        "Çiçek Pasajı",
                        "Masumiyet Müzesi",
                        "İstanbul Modern Sanat Müzesi",
                        "Pera Müzesi",
                        "Çemberlitaş Hamamı",
                        "Beyazit Kulesi",
                        "Fransız Geçidi",
                        "SALT Galata",
                        "Bomontiada",
                        "Rumeli Hisarı",
                        "Aya Nikola Rum Ortodoks Kilisesi",
                        "Sabancı Üniversitesi Sakıp Sabancı Müzesi",
                        "Ortaköy Sanat Galerisi",
                        "İş Bankası Müzesi",
                        "AK Bank Sanat Galerisi",
                        "Adam Mickiewicz Müzesi",
                        "Barbaros Hayrettin Heykeli",
                        "Binbirdirek Sarnıcı",
                        "Atatürk Heykeli",
                        "Atatürk Museum, Şişli",
                        "Büyük Saray Mozaikleri Müzesi",
                        "Laleli",
                        "Türk ve İslam Eserleri Müzesi",
                        "Beyazıt Türk Hamam Kültürü Müzesi",
                        "Galata Fotoğraf Akademisi",
                        "Istanbul Photography Museum",
                        "Askeri Müze",
                        "Koca Sinan Paşa Külliyesi",
                        "Kara Mustafa Paşa Külliyesi",
                        "Rezan Has Museum",
                        "Selimiye Hamami"
                        ]

        planned_names = []
        planned_locations = []
        if self.days < 5:
            planned_names = priority_list[:self.days * 8]
        else:
            planned_names = priority_list
        for location in planned_names:
            for place in self.possible_places:
                if place["tags"]["name"] == location:
                    planned_locations.append(place)

        self.plan = planned_locations

    def get_nodes(self, filename):
        """ Gets closest node information to the places """
        nearest_nodes = []
        self.location["lon"] = self.location.pop("lng")
        self.plan.insert(0, self.location)
        if not os.path.isfile(filename):
            for place in self.plan:
                nearest = ox.distance.nearest_nodes(self.graph, X=place["lon"], Y=place["lat"], return_dist=False)
                nearest_node = self.graph.nodes[nearest]
                nearest_node["id"] = nearest
                if "tags" in place:
                    if not any(d["name"] == place["tags"]["name"] for d in nearest_nodes):
                        if "name:en" in place["tags"]:
                            nearest_node["name"] = place["tags"]["name:en"]
                        else:
                            nearest_node["name"] = place["tags"]["name"]
                        nearest_node["speciality"] = place["tags"]["historic"] if "historic" in place["tags"] else place["tags"]["tourism"]
                        if "opening_hours" in place["tags"]:
                            nearest_node["additional"] = place["tags"]["opening_hours"]
                        nearest_nodes.append(nearest_node)
                elif "name" in place:
                    nearest_node["name"] = self.location["name"]
                    nearest_nodes.append(nearest_node)

            nearest_nodes = list(OrderedDict((frozenset(item.items()),item) for item in nearest_nodes).values())

            np.save("nearest_nodes", nearest_nodes)
        else:
            return np.load("nearest_nodes.npy", allow_pickle=True).tolist()
        return nearest_nodes

    def get_distance_matrix(self, nearest_nodes, filename):
        """ Find distance between nodes """
        if not os.path.isfile(filename):
            distance_matrix = []
            not_found = 0
            for source_node in nearest_nodes:
                distance_row = []
                for target_node in nearest_nodes:        
                    distance = 0
                    if source_node["id"] != target_node["id"]:
                        try:
                            distance = nx.shortest_path_length(self.graph, source_node["id"], target_node["id"], weight="length", method='dijkstra')
                        except Exception:
                            logger.error(f"{source_node} to {target_node} not found.")
                            not_found+=1
                            pass
                    distance_row.append(distance)
                distance_matrix.append(distance_row)
            np.save("distance_matrix", distance_matrix)
        else:
            distance_matrix = np.load("distance_matrix.npy", allow_pickle=True).tolist()
        self.distance_matrix = distance_matrix

pf = Pathfinder()
