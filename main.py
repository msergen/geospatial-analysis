import folium
import json
import math
import networkx as nx
import osmnx as ox
from folium import plugins
from loguru import logger
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from utils.ortool_manager import ort
from utils.folium_functions import mp
from utils.geospatial_functions import pf

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
data['num_vehicles'] = pf.days
data['demands'] = [1] * (len(nearest_nodes)-1)
data['demands'].insert(0, 0)
data['vehicle_capacities'] = [math.ceil((len(nearest_nodes)-1)/pf.days)] * pf.days
data['depot'] = 0

legend_colors = [ort.get_icon_color(day) for day in range(0, pf.days)]
legend_labels = ["Day {}".format(day) for day in range(1, pf.days + 1)]
m = mp.add_categorical_legend(m, 'Icon Legend', colors = legend_colors, labels = legend_labels)

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

def demand_callback(from_index):
    """Returns the demand of the node."""
    # Convert from routing variable Index to demands NodeIndex.
    from_node = manager.IndexToNode(from_index)
    return data['demands'][from_node]

demand_callback_index = routing.RegisterUnaryTransitCallback(
    demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0,  # null capacity slack
    data['vehicle_capacities'],  # vehicle maximum capacities
    True,  # start cumul to zero
    'Capacity')

transit_callback_index = routing.RegisterTransitCallback(distance_callback)

# Define cost of each arc.
routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

# Setting first solution heuristic.
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = (
routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
search_parameters.time_limit.FromSeconds(20)

# Solve the problem.
assignment = routing.SolveWithParameters(search_parameters)

if assignment:
    ort.print_solution(data, manager, routing, assignment)
    solution_routes = ort.get_solution_route(data, manager, routing, assignment);   
    counter = 0
    route_counter = 1
    color_counter = 0
    for solution_route in solution_routes:
      for index in solution_route:
          if index == 0:
            popup_title = '<h3><strong>Your Accommodation:</strong><br>'+nearest_nodes[index]["name"]+'</h3>'
          else:
            popup_title = '<h3><strong>'+str(route_counter)+'.</strong> '+nearest_nodes[index]["name"]+'</h3>'
          if "additional" in nearest_nodes[index]:
            popup_title += '<br><h4>Opening Hours: '+ str(nearest_nodes[index]["additional"]) + '</h4>'
          if "speciality" in nearest_nodes[index]:
            popup_title += '<br><h4>Description: '+ str(nearest_nodes[index]["speciality"]) + '</h4>'
          tooltip = popup_title

          if index == 0:
            folium.Marker(location=[nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title, tooltip=tooltip, 
                          icon=folium.Icon(border_color= "black", color='orange', icon="home", prefix='fa')).add_to(m)
          else:
            folium.Marker(location=[nearest_nodes[index]["y"], nearest_nodes[index]["x"]], popup=popup_title, tooltip=tooltip, 
                          icon=plugins.BeautifyIcon(icon="arrow-down",icon_shape="marker", number=route_counter, 
                          border_color= "black", background_color=ort.get_icon_color(color_counter))).add_to(m)
            route_counter += 1
          
          counter += 1
      color_counter += 1      
      counter = 0
      while counter < len(solution_route)-1:
          source_index = solution_route[counter];
          target_index = solution_route[counter+1];
          route = nx.shortest_path(pf.graph, nearest_nodes[source_index]['id'], nearest_nodes[target_index]['id'])        
          m = ox.plot_route_folium(pf.graph, route, route_map=m, popup_attribute='length', fit_bounds=True, color=ort.get_route_color(color_counter), opacity=0.8)        
          counter+=1
    m.save('itinerary.html')
    logger.success("Map saved as itinerary.html.")
