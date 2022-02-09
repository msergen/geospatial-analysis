from loguru import logger


class OrTools:

    def __init__(self):
        pass

    def print_solution(self, data, manager, routing, solution):
        """ Prints solution on console. """
        print(f'Objective: {solution.ObjectiveValue()}')
        total_distance = 0
        total_load = 0
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
            route_distance = 0
            route_load = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                plan_output += ' {0} Load({1}) -> '.format(node_index, route_load)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id)
            plan_output += ' {0} Load({1})\n'.format(manager.IndexToNode(index),
                                                    route_load)
            plan_output += 'Distance of the route: {}m\n'.format(route_distance)
            plan_output += 'Load of the route: {}\n'.format(route_load)
            print(plan_output)
            total_distance += route_distance
            total_load += route_load
        print('Total distance of all routes: {}m'.format(total_distance))
        print('Total load of all routes: {}'.format(total_load))

    def get_solution_route(self, data, manager, routing, assignment):
        """ Gets the solution from ORTools """
        solutions = []
        for vehicle_id in range(data['num_vehicles']):
            solution = []
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                solution.append(manager.IndexToNode(index))
                index = assignment.Value(routing.NextVar(index))
            solutions.append(solution)
        return solutions

    def get_route_color(self, index):
        """ Assign different colors for routes """
        colors = ['#BF360C','#FF5722','#5c480b','#1D2935','#686e66',
        '#837054', '#85805e', '#879068', '#F76E11', '#FF9F45', '#FFBC80', '#FFEEAD', '#D9534F', '#FFAD60', '#D3DEDC',
        '#92A9BD', '#7C99AC', '#FFEFEF', '#F0ECE3', '#DFD3C3', '#D84315', '#A68DAD']
        return colors[index%len(colors)]

    def get_icon_color(self, index):
        """ Assign colors for stops in the route """
        colors = ['cadetblue', 'green', 'purple', 'red', 'lightblue', 'gray', 
        'beige', 'pink', 'darkgreen', 'lightgray', 'orange']
        return colors[index%len(colors)]

ort = OrTools()
