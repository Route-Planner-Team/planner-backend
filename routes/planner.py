import pandas as pd
from sklearn.cluster import KMeans
from config import Config
import googlemaps
import requests
import polyline
from math import radians, sin, cos, sqrt, atan2
import json
import random
from bson.objectid import ObjectId

gmaps = googlemaps.Client(key=Config.GOOGLEMAPS_API_KEY)

# Necessary when using ML model
random.seed(101)

class RoutesPlanner():
    def __init__(self, config):
        self.config = config

    # Function transforms string address of our depot to coordinates
    def get_depot_coords(self, depot_address):
        return gmaps.geocode(depot_address)[0]['geometry']['location']

    # Function transforms string addresses of our locations to visit to coordinates
    def get_addresses_coords(self, addresses):
        addresses_coords = []
        for address in addresses:
            coords = gmaps.geocode(address)[0]['geometry']['location']
            addresses_coords.append(coords)
        return addresses_coords

    # Function uses KMeans to cluster location into clusters, df is our data in pandas DataFrame
    # Days is a number of cluster
    def cluster_addresses(self, df, days):
        model = KMeans(n_clusters=days)
        labels = model.fit_predict(df)
        df['label'] = labels
        return df

    # Function that prepare centers of p2 and p1
    def prepare_waypoints(self, p2_addresses, p1_addresses):

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
    def set_waypoints(self, avoid_tolls, start, addresses, end):

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

    # Function returns correct waypoints order for whole route (all priorities)
    def get_all_waypoints(self, avoid_tolls, priority3_addresses, priority2_addresses, priority1_addresses, depot, p2_center,
                          p1_center):

        # There are several combinations, number in a string says that there is at least one location with that priority
        # 321, 32, 31, 3, 21, 2, 1
        if len(priority3_addresses) >= 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) >= 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority3_addresses, p2_center)
            ordered_addresses = ordered_addresses + ordered_addresses1

            ordered_addresses2 = self.set_waypoints(avoid_tolls, ordered_addresses[-1], priority2_addresses, p1_center)
            ordered_addresses = ordered_addresses + ordered_addresses2

            ordered_addresses3 = self.set_waypoints(avoid_tolls, ordered_addresses[-1], priority1_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses3

        if len(priority3_addresses) >= 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) < 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority3_addresses, p2_center)
            ordered_addresses = ordered_addresses + ordered_addresses1

            ordered_addresses2 = self.set_waypoints(avoid_tolls, ordered_addresses[-1], priority2_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses2

        if len(priority3_addresses) >= 1 and len(priority2_addresses) < 1 and len(priority1_addresses) >= 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority3_addresses, p1_center)
            ordered_addresses = ordered_addresses + ordered_addresses1

            ordered_addresses2 = self.set_waypoints(avoid_tolls, ordered_addresses[-1], priority1_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses2

        if len(priority3_addresses) >= 1 and len(priority2_addresses) < 1 and len(priority1_addresses) < 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority3_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses1

        if len(priority3_addresses) < 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) >= 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority2_addresses, p1_center)
            ordered_addresses = ordered_addresses + ordered_addresses1

            ordered_addresses2 = self.set_waypoints(avoid_tolls, ordered_addresses[-1], priority1_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses2

        if len(priority3_addresses) < 1 and len(priority2_addresses) >= 1 and len(priority1_addresses) < 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority2_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses1

        if len(priority3_addresses) < 1 and len(priority2_addresses) < 1 and len(priority1_addresses) >= 1:
            ordered_addresses = []
            ordered_addresses1 = self.set_waypoints(avoid_tolls, depot, priority1_addresses, depot)
            ordered_addresses = ordered_addresses + ordered_addresses1

        return ordered_addresses

    # Function to create intermediates, which will be passed into request
    def create_json_intermediate(self, lat, lng):
        return {"location": {
                "latLng": {
                    "latitude": lat,
                    "longitude": lng
                }
            }
        }

    # Function to create request that will return distance, duration, polyline of whole route
    def get_distance_duration(self, avoid_tolls, waypoints):
        url = 'https://routes.googleapis.com/directions/v2:computeRoutes'
        headers = {
            'Content-Type': 'application/json',
            'X-Goog-Api-Key': Config.GOOGLEMAPS_API_KEY,
            'X-Goog-FieldMask': 'routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,routes.travelAdvisory.fuelConsumptionMicroliters'
        }

        intermediates = []
        for i in range(1, len(waypoints) - 1):
            lat, lng = waypoints[i]
            intermediate = self.create_json_intermediate(lat, lng)
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
        duration_s = float(duration_string[:-1])
        duration_min = duration_s / 60

        # Take polyline
        poly = data['routes'][0]['polyline']['encodedPolyline']

        return distance_km, duration_min, poly

    # Function to create request that will return fuel consumption between 2 points
    def get_fuel_between_points(self, avoid_tolls, origin, destination):
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
    def set_optimal_waypoints(self, avoid_tolls, df, depot_address):

        # For every cluster(route)
        routes = {}
        for label in range(0, len(df['label'].unique())):

            # Convert lat and lng to tuple
            depot = (depot_address['lat'], depot_address['lng'])
            df_label = df[df['label'] == label]

            # Create dataframe for every priority
            priority3_df = df_label[df_label['priority'] == 3][['lat', 'lng']]
            priority2_df = df_label[df_label['priority'] == 2][['lat', 'lng']]
            priority1_df = df_label[df_label['priority'] == 1][['lat', 'lng']]

            # Convert dataframe to list
            priority3_addresses = list(zip(priority3_df['lat'], priority3_df['lng']))
            priority2_addresses = list(zip(priority2_df['lat'], priority2_df['lng']))
            priority1_addresses = list(zip(priority1_df['lat'], priority1_df['lng']))

            # Get centers of priority2 and priority1
            p2_center, p1_center = self.prepare_waypoints(priority2_addresses, priority1_addresses)

            # Get ordered waypoints for whole route
            ordered_addresses = self.get_all_waypoints(avoid_tolls, priority3_addresses, priority2_addresses, priority1_addresses,
                                                  depot, p2_center, p1_center)

            # Whole route in the correct order, including depot
            waypoints = [depot] + ordered_addresses + [depot]

            # Calculate distance and duration for whole route
            total_distance, total_duration, polyline = self.get_distance_duration(avoid_tolls, waypoints)

            # Calculate fuel consumption
            total_fuel = 0
            for i in range(len(waypoints) - 1):
                origin = waypoints[i]
                destination = waypoints[i + 1]
                fuel_consumption = self.get_fuel_between_points(avoid_tolls, origin, destination)
                total_fuel = total_fuel + fuel_consumption

            routes[label] = [waypoints, total_distance, total_duration, total_fuel, polyline]

        return routes

    # Function take dict with optimized routes
    # Arranges a list of total distances
    def calculate_distances(self, routes):
        distances = []
        for route in routes:
            distances.append(routes[route][1])
        return distances

    # Function take dict with optimized routes
    # Arranges a list of total durations
    def calculate_durations(self, routes):
        durations = []
        for duration in routes:
            durations.append(routes[duration][2])
        return durations

    # Function take dict with optimized routes
    # Arranges a list of total fuel consumption
    def calculate_fuel(self, routes):
        fuels = []
        for fuel in routes:
            fuels.append(routes[fuel][3])
        return fuels

    # Function takes dict with optimized routes and list od total distances
    # In case a route breaks a distance or a duration daily limit we have to rearrange clusters (routes)
    # We move location from longest route, that is most similar (is the closest to the centroid) to the shortest route and put it in there
    def reorganise_routes(self, routes, distances, df_addresses):

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

    # We have to check if any route break daily limitations, and if so, we have to remove it from the list
    def check_limitations(self, all_routes, distance_limit, duration_limit):
        if distance_limit == -1:
            distance_limit = float('inf')
        if duration_limit == -1:
            duration_limit = float('inf')
        all_routes = [dis for dis in all_routes if all(val[1] <= distance_limit for val in dis.values())]
        if len(all_routes) == 0:
            return 'to_small_distance'
        all_routes = [dur for dur in all_routes if all(val[2] <= duration_limit for val in dur.values())]
        if len(all_routes) == 0:
            return 'to_small_duration'
        return all_routes

    # Function will choose routes that minimize preference given by user
    def choose_min_routes(self, all_routes, preference):
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

    # Function adds string address of a location
    def add_address_name(self, lat, lng):
        result = gmaps.reverse_geocode((lat, lng))
        address_components = result[0]['address_components']

        # Values valuable for us
        route = ''
        street_number = ''
        city = ''
        postal_code = ''
        country = ''
        for component in address_components:
            types = component['types']
            if 'route' in types:
                route = component['long_name']
            if 'street_number' in types:
                street_number = component['long_name']
            if 'postal_code' in types:
                postal_code = component['long_name']
            if 'locality' in types:
                city = component['long_name']
            if 'country' in types:
                country = component['long_name']
        address_name = "{} {}, {} {}, {}".format(route, street_number, postal_code, city, country)
        return address_name

    # Function changes names of output values
    def add_parameter_names_to_output(self, routes, addresses_priorities_dict):
        routes_dict = {}
        for key, value in routes.items():
            routes_dict[key] = {
                'coords': value[0],
                'completed': False,
                'date_of_completion': None,
                'distance_km': value[1],
                'duration_hours': value[2] / 60,
                'fuel_liters': value[3],
                'polyline': value[4],
                'route_number': key
            }

        for key in routes_dict:
            routes_dict[key]['coords'] = [{'latitude': coord[0],
                                           'longitude': coord[1],
                                           'name': self.add_address_name(coord[0], coord[1]),
                                           'priority': addresses_priorities_dict.get((coord[0], coord[1])),
                                           'location_number': i,
                                           'visited': None,
                                           'should_keep': None,
                                           'isDepot': i == 0 or i == len(routes_dict[key]['coords']) - 1} for i, coord in enumerate(routes_dict[key]['coords'])]
        return routes_dict

    def get_routes(self, depot_address, addresses, priorities, days, distance_limit, duration_limit, preferences, avoid_tolls):
        '''
        Function generates n routes, returns a dict of all addresses in correct order including depot
        Params:
        - depot address - address of our depot (string)
        - addresses - all addresses we have to visit (list of strings)
        - priorities - can be 1,2,3. Location with higher priority are firstly visited
        - days - indicates number of routes (int)
        - distance_limit - number of kilometers we can drive in one day (float)
        - duration_limit - number of min we can drive in one day (float)
        - preferences - can be 'distance','duration' or 'fuel', based of that, routes would be chosen by this parameter (str)
        - avoid_tolls - boolean
        '''

        # Convert depot address to coords
        depot_coords = self.get_depot_coords(depot_address)

        # Convert addresses of addresses to coords
        addresses_coords = self.get_addresses_coords(addresses)

        # Dict to save proper priority in db
        addresses_priorities_dict = {key: value for key, value in zip([(address['lat'], address['lng']) for address in addresses_coords], priorities)}

        # For further convenience we put data into pandas DataFrame
        df_addresses = pd.DataFrame(addresses_coords)

        # Create model and cluster locations into days
        df_addresses = self.cluster_addresses(df_addresses, days)

        # Add priority column
        df_addresses['priority'] = priorities

        # Prepare all points, set waypoints
        routes = self.set_optimal_waypoints(avoid_tolls, df_addresses, depot_coords)

        # Calculate distance, duration and consumption
        distances = self.calculate_distances(routes)
        durations = self.calculate_durations(routes)
        fuels = self.calculate_fuel(routes)

        # List with all routes, later we will choose one that minimize given preferences
        all_routes = []
        all_routes.append(routes)

        # We will generate more possible routes if there is more than 1 day
        # Loop has to be short because long loop would affect efficiency of our function badly
        # Additionally in every iteration there is google maps API request, so to many requests could cause fees!
        if days > 1:
            for day in range(1, days):
                df_addresses = self.reorganise_routes(routes, distances, df_addresses)
                routes = self.set_optimal_waypoints(avoid_tolls, df_addresses, depot_coords)
                distances = self.calculate_distances(routes)
                all_routes.append(routes)

        # Check if any route does not break daily limitation
        all_routes = self.check_limitations(all_routes, distance_limit, duration_limit)

        # Return routes that minimize given preferences
        if all_routes == 'to_small_distance':
            raise ValueError('To small distance limit')
        if all_routes == 'to_small_duration':
            raise ValueError('To small duration limit')
        if len(all_routes) == 0:
            raise ValueError('Can not compute routes for this parameters. Modify parameters.')
        else:
            if preferences == 'distance':
                routes = self.choose_min_routes(all_routes, 'distance')
            elif preferences == 'duration':
                routes = self.choose_min_routes(all_routes, 'duration')
            elif preferences == 'fuel':
                routes = self.choose_min_routes(all_routes, 'fuel')

        # Change names of output values
        routes = self.add_parameter_names_to_output(routes, addresses_priorities_dict)

        return routes
