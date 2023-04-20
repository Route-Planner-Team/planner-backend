import pandas as pd
from sklearn.cluster import KMeans
from geopy.distance import geodesic
from config import Config
import googlemaps

# Gdy robie from main import gmaps , dostaje Error loading ASGI app. Could not import module "main".
gmaps = googlemaps.Client(key=Config.GOOGLEMAPS_API_KEY)

class RoutesPlanner():
    def __init__(self, config):
        self.config = config

    def get_routes(self, depot_address, addresses, days, distance_limit, duration_limit, avg_fuel_consumption):
        '''
        Function generates n routes, returns a dict of all addresses in correct order including depot
        Params:
        - depot address - address of our depot (string)
        - addresses - all addresses we have to visit (list of strings)
        - days - indicates number of routes (int)
        - distance_limit - number of kilometers we can drive in one day (int)
        - duration_limit - number of hours we can drive in one day (int)
        - avg_fuel_consumption - average fuel consumption (int)
        '''

        # Function transforms string addres of our depot to coordinates
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

        # Function uses KMeans to cluster location into clusters, df is out data in pandas DataFrame
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
                    total_distance = (directions_result[0]['legs'][location]['distance'][
                                          'value'] / 1000) + total_distance
                    total_duration = (directions_result[0]['legs'][location]['duration'][
                                          'value'] / 3600) + total_duration

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
        # We move location from longest route that is most similar (is the closest to the centroid) to the shortest route and put it in there
        def reorganise_routes(routes, distances):

            # Function takie dict with routes
            # Convert data do DataFrame for further set_optimal_waypoints(df, depot_address) usage
            def routes_to_df(routes):
                df = pd.DataFrame(columns=['lat', 'lng', 'label'])

                for key in routes:
                    data = routes[key][0][1:-1]
                    df = df.append(pd.DataFrame({'lat': [coord[0] for coord in data],
                                                 'lng': [coord[1] for coord in data],
                                                 'label': key}))

                return df

            # Function takes dict with optimized routes and list od total distances
            # Funtion finds a location that will be reclustered
            def find_location_to_recluster(routes, distances):

                # Find indexes of longest and shortest route
                shortest_route = distances.index(min(distances))
                longest_route = distances.index(max(distances))

                # We have to check how many locations there are in longest route, in case it is only one location, we can not take away that point
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

        # In this loop, we can recluster points in case any limitations are broken
        # Loop has to be short because long loop would affect efficiency of our function badly
        # Additionaly in every iteration there is google maps API reques, so to many request could cause fees!
        for day in range(days):

            # Check if it is even possible to generate routes with passed paramaters
            if sum(distances) > distance_limit * days or sum(durations) > duration_limit * days:
                return ('Can not compute routes for this parameters. Modify parameters.')

            # Case to recluster some points
            if any(distance > distance_limit for distance in distances) or any(
                    duration > duration_limit for duration in durations):
                df_addresses = reorganise_routes(routes, distances)
                routes = set_optimal_waypoints(df_addresses, depot_coords)
                distances = calculate_distances(routes)

            else:
                break

        return routes