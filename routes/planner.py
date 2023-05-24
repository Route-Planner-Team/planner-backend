import pandas as pd
from sklearn.cluster import KMeans
from config import Config
import googlemaps
import requests
import polyline
from math import radians, sin, cos, sqrt, atan2
import json

# Gdy robie from main import gmaps , dostaje Error loading ASGI app. Could not import module "main".
gmaps = googlemaps.Client(key=Config.GOOGLEMAPS_API_KEY)

class RoutesPlanner():
    def __init__(self, config):
        self.config = config

    def get_routes(self, depot_address, addresses, priorities, days, distance_limit, duration_limit, preferences, avoid_tolls):
        '''
        Function generates n routes, returns a dict of all addresses in correct order including depot
        Params:
        - depot address - address of our depot (string)
        - addresses - all addresses we have to visit (list of strings)
        - priorities - can be 1,2,3. Location with higher priority are firstly visited
        - days - indicates number of routes (int)
        - distance_limit - number of kilometers we can drive in one day (int)
        - duration_limit - number of hours we can drive in one day (int)
        - preferences - can be 'distance','duration' or 'fuel', based of that, routes would be chosen by this parameter (str)
        - avoid_tolls - boolean
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

        # Add priority column
        df_addresses['priority'] = priorities

        # Function that prepare centers of p2 and p1
        def prepare_waypoints(p2_addresses, p1_addresses):

            # Create centroid for p2 and p1
            if len(p2_addresses) >= 1:
                p2_lat_center = list(map(lambda coord: coord[0], p2_addresses))
                p2_lng_center = list(map(lambda coord: coord[1], p2_addresses))
                p2_center = (sum(p2_lat_center) / len(p2_lat_center), sum(p2_lng_center) / len(p2_lng_center))
            else:
                p2_center = tuple()

            if len(p1_addresses) >= 1:
                p1_lat_center = list(map(lambda coord: coord[0], p1_addresses))
                p1_lng_center = list(map(lambda coord: coord[1], p1_addresses))
                p1_center = (sum(p1_lat_center) / len(p1_lat_center), sum(p1_lng_center) / len(p1_lng_center))
            else:
                p1_center = tuple()

            return p2_center, p1_center

        # Function to order waypoints
        def set_waypoints(start, addresses, end):

            if avoid_tolls is True:
                avoid = 'tolls'
            else:
                avoid = ''

            # Define waypoints
            waypoints = [start] + addresses + [end]
            # Direction from google
            directions_result = gmaps.directions(waypoints[0],
                                                 waypoints[-1],
                                                 waypoints=waypoints[1:-1],
                                                 mode='driving',
                                                 optimize_waypoints=True,
                                                 avoid=avoid)

            # List with ordered addresses indexes
            optimal_order = directions_result[0]['waypoint_order']

            # List with ordered addresses
            ordered_addresses = [addresses[i] for i in optimal_order]

            return ordered_addresses

        # Funtion returns correct waypoints order for whole route (all priorities)
        def get_all_waypoints(priority3_addresses, priority2_addresses, priority1_addresses, depot, p2_center,
                              p1_center):

            # There are several combinations, number in a string says that there is at least one location with that priority
            # 321, 32, 31, 3, 21, 2, 1
            if len(priority3_addresses) >= 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) >= 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority3_addresses, p2_center)
                ordered_addresses = ordered_addresses + ordered_addresses1

                ordered_addresses2 = set_waypoints(ordered_addresses[-1], priority2_addresses, p1_center)
                ordered_addresses = ordered_addresses + ordered_addresses2

                ordered_addresses3 = set_waypoints(ordered_addresses[-1], priority1_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses3

            if len(priority3_addresses) >= 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) < 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority3_addresses, p2_center)
                ordered_addresses = ordered_addresses + ordered_addresses1

                ordered_addresses2 = set_waypoints(ordered_addresses[-1], priority2_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses2

            if len(priority3_addresses) >= 1 and len(priority2_addresses) < 1 and len(priority1_addresses) >= 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority3_addresses, p1_center)
                ordered_addresses = ordered_addresses + ordered_addresses1

                ordered_addresses2 = set_waypoints(ordered_addresses[-1], priority1_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses2

            if len(priority3_addresses) >= 1 and len(priority2_addresses) < 1 and len(priority1_addresses) < 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority3_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses1

            if len(priority3_addresses) < 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) >= 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority2_addresses, p1_center)
                ordered_addresses = ordered_addresses + ordered_addresses1

                ordered_addresses2 = set_waypoints(ordered_addresses[-1], priority1_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses2

            if len(priority3_addresses) < 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) < 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority2_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses1

            if len(priority3_addresses) < 1 and len(priority2_addresses) < 1 and len(priority1_addresses) >= 1:
                ordered_addresses = []
                ordered_addresses1 = set_waypoints(depot, priority1_addresses, depot)
                ordered_addresses = ordered_addresses + ordered_addresses1

            return ordered_addresses

        # Function to create intermediates, which will be passed into request
        def create_json_intermediate(lat, lng):
            return {"location": {
                "latLng": {
                    "latitude": lat,
                    "longitude": lng
                }
            }
            }

        # Function to create request that will return distance, duration, polyline of whole route
        def get_distance_duration(waypoints):
            url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': Config.GOOGLEMAPS_API_KEY,
                'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.fuelConsumptionMicroliters'
            }

            intermediates = []
            for i in range(1, len(waypoints) - 1):
                lat, lng = waypoints[i]
                intermediate = create_json_intermediate(lat, lng)
                intermediates.append(intermediate)

            if avoid_tolls is True:
                avoid = True
            else:
                avoid = False

            payload = {
                "origin": {
                    "location": {
                        "latLng": {
                            "latitude": waypoints[0][0],
                            "longitude": waypoints[0][1]
                        }
                    }
                },
                "destination": {
                    "location": {
                        "latLng": {
                            "latitude": waypoints[-1][0],
                            "longitude": waypoints[-1][1]
                        }
                    }
                },
                "intermediates": intermediates,
                "routeModifiers": {
                    "vehicleInfo": {
                        "emissionType": "GASOLINE"
                    }
                },

                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
                "routeModifiers": {
                    "avoidTolls": avoid
                },
                "extraComputations": ["FUEL_CONSUMPTION"]
            }

            response = requests.post(url, headers=headers, data=json.dumps(payload))

            data = response.json()

            # Take whole distance
            distance_m = data['routes'][0]['distanceMeters']
            distance_km = distance_m / 1000

            # Take whole duration
            duration_string = data['routes'][0]['duration']
            duration_s = int(duration_string[:-1])
            duration_h = duration_s / 3600

            # Take polyline
            poly = data['routes'][0]['polyline']['encodedPolyline']

            return distance_km, duration_h, poly

        # Function to create request that will return fuel consumption between 2 points
        def get_fuel_between_points(origin, destination):
            url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
            headers = {
                'Content-Type': 'application/json',
                'X-Goog-Api-Key': Config.GOOGLEMAPS_API_KEY,
                'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.fuelConsumptionMicroliters'
            }

            if avoid_tolls is True:
                avoid = True
            else:
                avoid = False

            payload = {
                "origin": {
                    "location": {
                        "latLng": {
                            "latitude": origin[0],
                            "longitude": origin[1]
                        }
                    }
                },
                "destination": {
                    "location": {
                        "latLng": {
                            "latitude": destination[0],
                            "longitude": destination[1]
                        }
                    }
                },
                "routeModifiers": {
                    "vehicleInfo": {
                        "emissionType": "GASOLINE"
                    }
                },
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
                "routeModifiers": {
                    "avoidTolls": avoid
                },
                "extraComputations": ["FUEL_CONSUMPTION"]
            }

            response = requests.post(url, headers=headers, data=json.dumps(payload))

            data = response.json()

            # Take fuel in Microliters
            fuel_micro = data['routes'][0]['travelAdvisory']['fuelConsumptionMicroliters']
            fuel_liters = int(fuel_micro) / 1000000

            return fuel_liters

        # Function takes data in DataFrame format and converted coordinates of our addresses
        # In this function we set optimal order of the waypoints in every route
        def set_optimal_waypoints(df, depot_address):

            # For every cluster(route)
            routes = {}
            for label in range(0, len(df['label'].unique())):

                # Convert lat and lng to tuple
                depot = (depot_address['lat'], depot_address['lng'])
                df_label = df[df['label'] == label]

                # Create datafrme for every priority
                priority3_df = df_label[df_label['priority'] == 3][['lat', 'lng']]
                priority2_df = df_label[df_label['priority'] == 2][['lat', 'lng']]
                priority1_df = df_label[df_label['priority'] == 1][['lat', 'lng']]

                # Convert dataframe to list
                priority3_addresses = list(zip(priority3_df['lat'], priority3_df['lng']))
                priority2_addresses = list(zip(priority2_df['lat'], priority2_df['lng']))
                priority1_addresses = list(zip(priority1_df['lat'], priority1_df['lng']))

                # Get centers of priority2 and priority1
                p2_center, p1_center = prepare_waypoints(priority2_addresses, priority1_addresses)

                # Get ordered waypoints for whole route
                ordered_addresses = get_all_waypoints(priority3_addresses, priority2_addresses, priority1_addresses,
                                                      depot, p2_center, p1_center)

                # Whole route in the correct order, including depot
                waypoints = [depot] + ordered_addresses + [depot]

                # Calculate distance and duration for whole route
                total_distance, total_duration, polyline = get_distance_duration(waypoints)

                # Calculate fuel consumption
                total_fuel = 0
                for i in range(len(waypoints) - 1):
                    origin = waypoints[i]
                    destination = waypoints[i + 1]
                    fuel_consumption = get_fuel_between_points(origin, destination)
                    total_fuel = total_fuel + fuel_consumption

                routes[label] = [waypoints, total_distance, total_duration, total_fuel, polyline]

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

        # Function take dict with optimized routes
        # Arranges a list of total fuel consumption
        def calculate_fuel(routes):
            fuels = []
            for fuel in routes:
                fuels.append(routes[fuel][3])
            return fuels

        distances = calculate_distances(routes)
        durations = calculate_durations(routes)
        fuels = calculate_fuel(routes)

        # Function takes dict with optimized routes and list od total distances
        # In case a route breaks a distance or a duration daily limit we have to rearrange clusters (routes)
        # We move location from longest route, that is most similar (is the closest to the centroid) to the shortest route and put it in there
        def reorganise_routes(routes, distances):

            # Function take dict with routes
            # Convert data do DataFrame for further set_optimal_waypoints(df, depot_address) usage
            def routes_to_df(routes, df_addresses):
                df_list = []
                for key in routes:
                    data = routes[key][0][1:-1]
                    df_list.append(pd.DataFrame({'lat': [coord[0] for coord in data],
                                                 'lng': [coord[1] for coord in data],
                                                 'label': key}))

                df = pd.concat(df_list, ignore_index=True)
                # We need to add priority column
                merged_df = pd.merge(df, df_addresses[['lat', 'lng', 'priority']], on=['lat', 'lng'], how='inner')

                return merged_df

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

                # Function to calculate distance between 2 coords
                # Packages which do this, sometimes return an error
                def calculate_distance(lat1, lon1, lat2, lon2):
                    earth_radius = 6371.0

                    # Convert the coordinates from degrees to radians
                    lat1_rad = radians(lat1)
                    lon1_rad = radians(lon1)
                    lat2_rad = radians(lat2)
                    lon2_rad = radians(lon2)

                    # Differences between the coordinates
                    dlat = lat2_rad - lat1_rad
                    dlon = lon2_rad - lon1_rad

                    # Haversine formula
                    a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
                    c = 2 * atan2(sqrt(a), sqrt(1 - a))
                    distance = earth_radius * c

                    return distance

                # Find closest point to centroid from longest route
                min_distance = float('inf')
                closest_location = None
                for location in routes[longest_route][0][1:-1]:
                    distance = calculate_distance(center[0], center[1], location[0], location[1])
                    if distance < min_distance:
                        min_distance = distance
                        closest_location = location

                return shortest_route, longest_route, closest_location

            shortest_route, longest_route, location = find_location_to_recluster(routes, distances)

            df = routes_to_df(routes, df_addresses)

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
                index_of_min_sum = min(range(len(all_routes)),
                                       key=lambda i: sum(value[1] for value in all_routes[i].values()))
            elif preference == 'duration':
                index_of_min_sum = min(range(len(all_routes)),
                                       key=lambda i: sum(value[2] for value in all_routes[i].values()))
            elif preference == 'fuel':
                index_of_min_sum = min(range(len(all_routes)),
                                       key=lambda i: sum(value[3] for value in all_routes[i].values()))
            return all_routes[index_of_min_sum]

        # Return routes that minimize given preferences
        if len(all_routes) == 0:
            return ('Can not compute routes for this parameters. Modify parameters.')
        else:
            if preferences == 'distance':
                routes = choose_min_routes(all_routes, 'distance')
            elif preferences == 'duration':
                routes = choose_min_routes(all_routes, 'duration')
            elif preferences == 'fuel':
                routes = choose_min_routes(all_routes, 'fuel')

            def add_parameter_names_to_output(routes):
                routes_dict = {}
                for key, value in routes.items():
                    routes_dict[key] = {
                        'coords': value[0],
                        'distance_km': value[1],
                        'duration_hours': value[2],
                        'fuel_liters': value[3],
                        'polyline': value[4]
                    }
                for key in routes_dict:
                    routes_dict[key]['coords'] = [{'latitude': coord[0], 'longitude': coord[1]} for coord in routes_dict[key]['coords']]
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