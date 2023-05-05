import pandas as pd
from sklearn.cluster import KMeans
from geopy.distance import geodesic
from config import Config
import googlemaps
import requests
import polyline

# Gdy robie from main import gmaps , dostaje Error loading ASGI app. Could not import module "main".
gmaps = googlemaps.Client(key=Config.GOOGLEMAPS_API_KEY)

class RoutesPlanner():
    def __init__(self, config):
        self.config = config

    def get_routes(self, depot_address, addresses, days, distance_limit, duration_limit, preferences):
        '''
        Function generates n routes, returns a dict of all addresses in correct order including depot
        Params:
        - depot address - address of our depot (string)
        - addresses - all addresses we have to visit (list of strings)
        - days - indicates number of routes (int)
        - distance_limit - number of kilometers we can drive in one day (int)
        - duration_limit - number of hours we can drive in one day (int)
        - preferences - can be 'distance' or 'duration', based of that, routes would be chosen by this parameter (str)
        '''

        # Function transforms string address of our depot to coordinates
        def get_depot_coords(depot_address):
            return gmaps.geocode(depot_address)[0]['geometry']['location']

        # Function transforms string addresses of our locations to visit to coordinates
        def get_addresses_coords(addresses):
            addresses_coords = []
            for address in addresses:
                coords = gmaps.geocode(address)[0]['geometry']['location']
                addresses_coords.append(coords)
            return addresses_coords

        depot_coords = get_depot_coords(depot_address)

        addresses_coords = get_addresses_coords(addresses)

        # Function uses KMeans to cluster location into clusters, df is our data in pandas DataFrame
        # Days is a number of cluster
        def cluster_addresses(df, days):
            model = KMeans(n_clusters=days)
            labels = model.fit_predict(df)
            df['label'] = labels
            return df

        # For further convenience we put data into pandas DataFrame
        df_addresses = pd.DataFrame(addresses_coords)
        df_addresses = cluster_addresses(df_addresses, days)

        # Function takes data in DataFrame format and converted coordinates of our addresses
        # In this function we set optimal order of the waypoints in every route
        def set_optimal_waypoints(df, depot_address):

            # For every cluster(route)
            routes = {}
            for label in range(0, len(df['label'].unique())):

                # Convert lat and lng to tuple
                depot = (depot_address['lat'], depot_address['lng'])
                df_label = df[df['label'] == label]
                addresses = list(zip(df_label['lat'], df_label['lng']))

                # Define waypoints
                waypoints = [depot] + addresses + [depot]

                # Direction from google
                directions_result = gmaps.directions(waypoints[0],
                                                     waypoints[-1],
                                                     waypoints=waypoints[1:-1],
                                                     mode='driving',
                                                     optimize_waypoints=True)

                # List with ordered addresses indexes
                optimal_order = directions_result[0]['waypoint_order']

                # List with ordered addresses
                ordered_addresses = [addresses[i] for i in optimal_order]

                # List that contains every location (including depot) in order
                whole_route = ordered_addresses.copy()
                whole_route.insert(0, depot)
                whole_route.append(depot)

                # We want to get distance and duration of a whole route
                total_distance = 0  # in km
                total_duration = 0  # in hours
                for location in range(len(whole_route) - 1):
                    total_distance = (directions_result[0]['legs'][location]['distance']['value'] / 1000) + total_distance
                    total_duration = (directions_result[0]['legs'][location]['duration']['value'] / 3600) + total_duration

                routes[label] = [whole_route, total_distance, total_duration]

            return routes

        routes = set_optimal_waypoints(df_addresses, depot_coords)

        # Function take dict with optimized routes
        # Arranges a list of total distances
        def calculate_distances(routes):
            distances = []
            for route in routes:
                distances.append(routes[route][1])
            return distances

        # Function take dict with optimized routes
        # Arranges a list of total durations
        def calculate_durations(routes):
            durations = []
            for duration in routes:
                durations.append(routes[duration][2])
            return durations

        distances = calculate_distances(routes)
        durations = calculate_durations(routes)

        # Function takes dict with optimized routes and list od total distances
        # In case a route breaks a distance or a duration daily limit we have to rearrange clusters (routes)
        # We move location from longest route, that is most similar (is the closest to the centroid) to the shortest route and put it in there
        def reorganise_routes(routes, distances):

            # Function take dict with routes
            # Convert data do DataFrame for further set_optimal_waypoints(df, depot_address) usage
            def routes_to_df(routes):
                df_list = []
                for key in routes:
                    data = routes[key][0][1:-1]
                    df_list.append(pd.DataFrame({'lat': [coord[0] for coord in data],
                                                 'lng': [coord[1] for coord in data],
                                                 'label': key}))

                df = pd.concat(df_list, ignore_index=True)
                return df

            # Function takes dict with optimized routes and list od total distances
            # Function finds a location that will be reclustered
            def find_location_to_recluster(routes, distances):

                # Find indexes of longest and shortest route
                shortest_route = distances.index(min(distances))
                longest_route = distances.index(max(distances))

                # We have to check how many locations are there in longest route, in case it is only one location, we can not take away that point
                # from the route, because route would become empty
                while len(routes[longest_route][0]) < 4:
                    longest_route = distances.index(max(distances))
                    if sum(distances) == distances[shortest_route]:
                        longest_route = shortest_route
                        break
                    distances[longest_route] = 0

                # Calculate centroid for shortest route, including depot
                lat_center = [p[0] for p in routes[shortest_route][0]]
                lng_center = [p[1] for p in routes[shortest_route][0]]
                center = (sum(lat_center) / len(routes[0][0]), sum(lng_center) / len(routes[0][0]))

                # Find closest point to centroid from longest route
                min_distance = float('inf')
                closest_location = None
                for location in routes[longest_route][0][1:-1]:
                    distance = geodesic(center, location).kilometers
                    if distance < min_distance:
                        min_distance = distance
                        closest_location = location

                return shortest_route, longest_route, closest_location

            shortest_route, longest_route, location = find_location_to_recluster(routes, distances)

            df = routes_to_df(routes)

            # Change the value in column 'label' for a reclustered point
            df.loc[(df['lat'] == location[0]) & (df['lng'] == location[1]), 'label'] = shortest_route

            return df

        # List with all routes, later we will choose one that minimize given preferences
        all_routes = []
        all_routes.append(routes)

        # We will generate more possible routes if there is more than 1 day
        # Loop has to be short because long loop would affect efficiency of our function badly
        # Additionally in every iteration there is google maps API request, so to many requests could cause fees!
        if days > 1:
            for day in range(1, days):
                df_addresses = reorganise_routes(routes, distances)
                routes = set_optimal_waypoints(df_addresses, depot_coords)
                distances = calculate_distances(routes)
                all_routes.append(routes)

        # We have to check if any route break daily limitations, and if so, we have to remove it from the list
        def check_limitations(all_routes):
            all_routes = [dis for dis in all_routes if all(val[1] <= distance_limit for val in dis.values())]
            all_routes = [dur for dur in all_routes if all(val[2] <= duration_limit for val in dur.values())]
            return all_routes

        all_routes = check_limitations(all_routes)

        # Function will choose routes that minimize preference given by user
        def choose_min_routes(all_routes, preference):
            if preference == 'distance':
                index_of_min_sum = min(range(len(all_routes)), key=lambda i: sum(value[1] for value in all_routes[i].values()))
            elif preference == 'duration':
                index_of_min_sum = min(range(len(all_routes)), key=lambda i: sum(value[2] for value in all_routes[i].values()))
            return all_routes[index_of_min_sum]

        # Return routes that minimize given preferences
        if len(all_routes) == 0:
            return ('Can not compute routes for this parameters. Modify parameters.')
        else:
            if preferences == 'distance':
                routes = choose_min_routes(all_routes, 'distance')
            elif preferences == 'duration':
                routes = choose_min_routes(all_routes, 'duration')

        # Output would be clearer to read
        # def add_parameter_names_to_output(routes):
        #     routes_dict = {}
        #     for key, value in routes.items():
        #         routes_dict[key] = {
        #             'coords': value[0],
        #             'distance_km': value[1],
        #             'duration_hours': value[2]
        #         }
        #     return routes_dict
            def add_parameter_names_to_output(routes):
                routes_dict = {}
                for key, value in routes.items():
                    routes_dict[key] = {
                        'coords': value[0],
                        'distance_km': value[1],
                        'duration_hours': value[2]
                    }
                for key in routes_dict:
                    routes_dict[key]['coords'] = [[coord[0], coord[1]] for coord in routes_dict[key]['coords']]
                return routes_dict

        routes = add_parameter_names_to_output(routes)

        return routes

    def calculate_route(self, addresses):
        # addresses = [
        #     "1600 Amphitheatre Parkway, Mountain View, CA",
        #     "345 Park Ave, San Jose, CA",
        #     "1 Hacker Way, Menlo Park, CA",
        #     "350 Rhode Island St, San Francisco, CA"
        # ]

        response = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": addresses[0],
                "destination": addresses[-1],
                "key": self.config.GOOGLEMAPS_API_KEY
            }
        )

        if response.status_code != 200:
            return {"error": "Failed to calculate route"}

        data = response.json()
        # print(data)

        points = []

        steps = data['routes'][0]['legs'][0]['steps']

        tmp_array = []
        for step in steps:
            polyline_str = step['polyline']['points']
            tmp_array.append(polyline_str)

            decoded_polyline = polyline.decode(polyline_str)


            points.extend(decoded_polyline)

        return {"route": points}