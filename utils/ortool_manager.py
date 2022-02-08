from __future__ import print_function
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import osmnx as ox
import requests
import json
import networkx as nx
import folium
import numpy as np
import os.path
from loguru import logger
import geocoder
import re

class OrTools:
    def __init__(self):
        pass

    def print_solution(self, manager, routing, assignment):
        """Prints assignment on console."""
        logger.info('Total Distance: {} meters'.format(assignment.ObjectiveValue()))
        index = routing.Start(0)
        plan_output = 'Route to follow:\n'
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += ' {} ->'.format(manager.IndexToNode(index))
            previous_index = index
            index = assignment.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        plan_output += ' {}\n'.format(manager.IndexToNode(index))
        logger.success(plan_output)

    def get_solution_route(self, manager, routing, assignment):
        """ Gets the solution from ORTools """
        solution = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            solution.append(manager.IndexToNode(index))
            index = assignment.Value(routing.NextVar(index))
        return solution

    def get_route_color(self, index):
        """ Assign different colors for routes """
        colors = ['#BF360C','#D84315','#E64A19','#F4511E','#FF5722','#FF7043','#FF8A65','#FFAB91', '#bb9215', '#557e86',
        '#806049', '#837054', '#85805e', '#879068', '#F76E11', '#FF9F45', '#FFBC80', '#FC4F4F', '#96CEB4', '#FFEEAD', '#D9534F', '#FFAD60', '#D3DEDC',
        '#92A9BD', '#7C99AC', '#FFEFEF', '#F0ECE3', '#DFD3C3', '#C7B198', '#A68DAD']
        return colors[index%len(colors)]

    def get_icon_color(self, index):
        """ Assign colors for stops in the route """
        colors = ['darkred', 'cadetblue', 'lightgreen', 'green', 'purple', 'red', 'lightblue', 'gray', 
        'beige', 'pink', 'darkgreen', 'lightgray', 'orange']
        return colors[index%len(colors)]

ort = OrTools()
