import osmnx as ox
from loguru import logger
from utils.geospatial_functions import pf
import json
from geopy.geocoders import Nominatim
import geocoder
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from utils.ortool_manager import ort
import folium
import networkx as nx
from folium import plugins

# Initialize map according to Istanbul
m = folium.Map(location=[41, 28.57])

pf.build_graph()

pf.load_graph('istanbul.graphml')

filename = "touristic_spots.json"
url = "http://overpass-api.de/api/interpreter"
query = """
[out:json];
area["name"="İstanbul"]->.a;
(
  node["tourism"~"artwork|attraction|zoo|theme_park|museum|information|gallery|aquarium"]["name"](area.a);
  node["historic"~"monument"]["name"](area.a);
);

out center;                                                                                                                       
"""

pf.get_overpass_data(filename, url, query)

with open(filename, 'r') as f:
    data = json.load(f)
    logger.info(f"POI List read from {filename}.")

pf.get_user_location_by_name()

pf.get_trip_days()

pf.get_possible_touristic_places(json_file="touristic_spots.json")

pf.form_touristic_places()

nearest_nodes = pf.get_nodes("nearest_nodes.npy")

pf.get_distance_matrix(nearest_nodes, "distance_matrix.npy")

data = {}
data['distance_matrix'] = pf.distance_matrix
data['num_vehicles'] = 1
data['depot'] = 0

# Create the routing index manager.
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                      data['num_vehicles'], data['depot'])

# Create Routing Model.
routing = pywrapcp.RoutingModel(manager)

def distance_callback(from_index, to_index):
  """Returns the distance between the two nodes."""
  # Convert from routing variable Index to distance matrix NodeIndex.
  from_node = manager.IndexToNode(from_index)
  to_node = manager.IndexToNode(to_index)
  return data['distance_matrix'][from_node][to_node]

transit_callback_index = routing.RegisterTransitCallback(distance_callback)

# Define cost of each arc.
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Setting first solution heuristic.
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

# Solve the problem.
assignment = routing.SolveWithParameters(search_parameters)

if assignment:
    ort.print_solution(manager, routing, assignment)
    solution_route = ort.get_solution_route(manager, routing, assignment);   
    counter = 0
    for index in solution_route:
        if index == 0:
          popup_title = '<h3><strong>Your Accommodation:</strong><br>'+nearest_nodes[index]["name"]+'</h3>'
        else:
          popup_title = '<h3><strong>'+str(counter)+'.</strong> '+nearest_nodes[index]["name"]+'</h3>'
        if "additional" in nearest_nodes[index]:
          popup_title += '<br><h4>Opening Hours: '+ str(nearest_nodes[index]["additional"]) + '</h4>'
        if "speciality" in nearest_nodes[index]:
          popup_title += '<br><h4>Description: '+ str(nearest_nodes[index]["speciality"]) + '</h4>'
        tooltip = popup_title

        if index == 0:
          folium.Marker(location=[nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title, tooltip=tooltip, icon=folium.Icon(color=ort.get_icon_color(index), icon="home", prefix='fa')).add_to(m)
        if index == solution_route[len(solution_route)-1]:
          folium.Marker(location=[nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title, tooltip=tooltip, icon=folium.Icon(color="black", icon="flag-checkered", prefix='fa')).add_to(m)
        if (index != 0) and (index != solution_route[len(solution_route)-1]):
          folium.Marker(location=[nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title, tooltip=tooltip, icon=plugins.BeautifyIcon(icon="arrow-down",icon_shape="marker", number=counter, 
          border_color= "black", background_color=ort.get_icon_color(index))).add_to(m)

        counter += 1
          
    counter = 0
    while counter < len(solution_route)-1:
        source_index = solution_route[counter];
        target_index = solution_route[counter+1];
        route = nx.shortest_path(pf.graph, nearest_nodes[source_index]['id'], nearest_nodes[target_index]['id'])        
        m = ox.plot_route_folium(pf.graph, route, route_map=m, popup_attribute='length', fit_bounds=True, color=ort.get_route_color(counter))        
        counter+=1
    m.save('itinerary.html')
    logger.success("Map saved as itinerary.html.")
