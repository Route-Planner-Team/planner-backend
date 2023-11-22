from bson import json_util
from bson.objectid import ObjectId
from firebase_admin import auth, credentials
from loguru import logger
from passlib.context import CryptContext
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult
from fastapi import HTTPException

import datetime
from dateutil.parser import parse

from config import Config

cfg = Config()

from routes.planner import RoutesPlanner
routes_planner = RoutesPlanner(cfg)


class RouteRepository():
    def __init__(self, config):
        self.config = config
        self.client: MongoClient = MongoClient(self.config.MONGO)
        self.db: Database = self.client.route_db
        self.routes_collection: Collection = self.client.route_db.routes
        self.visited_collection: Collection = self.client.route_db.visited_points
        self.locations_collection: Collection = self.client.route_db.locations
        logger.info("Inited routes repo")

    # documents must have only string keys, key was 0
    def convert_dict_keys_to_str(self, dictionary):
        if isinstance(dictionary, dict):
            new_dict = {}
            for key, value in dictionary.items():
                new_key = str(key)
                new_value = self.convert_dict_keys_to_str(value)
                new_dict[new_key] = new_value
            return new_dict
        else:
            return dictionary

    def create_user_route(self, uid: str, body: dict, days, distance_limit, duration_limit, preferences, avoid_tolls, routes_id):
        firebase_user = auth.get_user(uid)

        document = self.convert_dict_keys_to_str(body)

        document['user_firebase_id'] = uid
        document['email'] = firebase_user.email
        document['days'] = days
        document['distance_limit'] = distance_limit
        document['duration_limit'] = duration_limit
        document['preferences'] = preferences
        document['avoid_tolls'] = avoid_tolls
        document['routes_completed'] = False
        document['date_of_completion'] = None
        current_datetime = datetime.datetime.now()
        document['generation_date'] = f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}'
        document['name'] = f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}' #date as default

        if routes_id is not None:
            routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
            if routes is not None:
                completed_routes = self.get_completed_routes(routes)
                document, new_days = self.merge_routes(document, completed_routes)
                document['days'] = new_days
                self.routes_collection.replace_one({"_id": ObjectId(routes_id)}, document)
                document['routes_id'] = str(routes_id)
                transformed_document = self.transform_format(document, False)
                return transformed_document

        res = self.routes_collection.insert_one(dict(document))

        document['routes_id'] = str(res.inserted_id)

        transformed_document = self.transform_format(document, False)

        return transformed_document

    def transform_format(self, document, all_routes=False):

        if all_routes is True:
            routes = []
            for key_document, value_document in document.items():
                if isinstance(value_document, dict):
                    subRoutes = []
                    for key_routes, value_routes in value_document.items():
                        if isinstance(value_routes, dict):
                            coords = []
                            for location in value_routes["coords"]:
                                point = {
                                    "latitude": location["latitude"],
                                    "longitude": location["longitude"],
                                    "name": location["name"],
                                    "priority": location["priority"],
                                    "location_number": location["location_number"],
                                    "visited": location["visited"],
                                    "should_keep": location["should_keep"],
                                    "polyline_to_next_point": location["polyline_to_next_point"],
                                    "isDepot": location["isDepot"]
                                }
                                coords.append(point)
                            route = {
                                "coords": coords,
                                "completed": value_routes["completed"],
                                "date_of_completion": value_routes["date_of_completion"],
                                "distance_km": value_routes["distance_km"],
                                "duration_hours": value_routes["duration_hours"],
                                "fuel_liters": value_routes["fuel_liters"],
                                "polyline": value_routes["polyline"],
                                "route_number": value_routes["route_number"]
                            }
                            subRoutes.append(route)
                    output_data = {"subRoutes": subRoutes,
                         "user_firebase_id": value_document["user_firebase_id"],
                         "email": value_document["email"],
                         "days": value_document["days"],
                         "distance_limit": value_document["distance_limit"],
                         "duration_limit": value_document["duration_limit"],
                         "preferences": value_document["preferences"],
                         "avoid_tolls": value_document["avoid_tolls"],
                         "routes_completed": value_document["routes_completed"],
                         "date_of_completion": value_document["date_of_completion"],
                         "generation_date": value_document["generation_date"],
                         "name": value_document["name"],
                         "routes_id": value_document["routes_id"]
                         }
                    routes.append(output_data)

            return {"routes": routes}

        subRoutes = []

        for key_document, value_document in document.items():
            if isinstance(value_document, dict):
                coords = []
                for location in value_document["coords"]:
                    point = {
                        "latitude": location["latitude"],
                        "longitude": location["longitude"],
                        "name": location["name"],
                        "priority": location["priority"],
                        "location_number": location["location_number"],
                        "visited": location["visited"],
                        "should_keep": location["should_keep"],
                        "polyline_to_next_point": location["polyline_to_next_point"],
                        "isDepot": location["isDepot"]
                    }
                    coords.append(point)
                route = {
                    "coords": coords,
                    "completed": value_document["completed"],
                    "date_of_completion": value_document["date_of_completion"],
                    "distance_km": value_document["distance_km"],
                    "duration_hours": value_document["duration_hours"],
                    "fuel_liters": value_document["fuel_liters"],
                    "polyline": value_document["polyline"],
                    "route_number": value_document["route_number"]
                }
                subRoutes.append(route)

        output_data = {"routes": [
                {"subRoutes": subRoutes,
                "user_firebase_id": document["user_firebase_id"],
                "email": document["email"],
                "days": document["days"],
                "distance_limit": document["distance_limit"],
                "duration_limit": document["duration_limit"],
                "preferences": document["preferences"],
                "avoid_tolls": document["avoid_tolls"],
                "routes_completed": document["routes_completed"],
                "date_of_completion": document["date_of_completion"],
                "generation_date": document["generation_date"],
                "name": document["name"],
                "routes_id": document["routes_id"]
                }
            ]
        }

        return output_data


    def get_completed_routes(self, routes):
        keys_to_remove = []
        for key, value in routes.items():
            if isinstance(value, dict):
                if value['completed'] is False:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del routes[key]
        return routes

    def merge_routes(self, document, completed_routes):
        # Merge documents with, change key for added routes, change rute number
        new_key = 0
        while str(new_key) in document:
            new_key += 1

        for key, value in completed_routes.items():
            if isinstance(value, dict):
                document[str(new_key)] = value
                value['route_number'] = new_key
                new_key += 1

        numeric_keys = [key for key in document if key.isdigit()]
        other_keys = [key for key in document if not key.isdigit()]
        numeric_keys.sort()
        sorted_doc = {**{key: document[key] for key in numeric_keys},**{key: document[key] for key in other_keys}}

        return sorted_doc, new_key

    def get_user_route(self, uid: str, active=False, for_stats=False):
        cursor = self.routes_collection.find({"user_firebase_id": uid})
        documents = list(cursor)

        all_routes = []

        for document in documents:
            document['routes_id'] = str(document.pop('_id'))
            all_routes.append(document)

        # Returns routes where completed is False
        if active is True:
            # Filter documents
            active_routes = []
            for document in all_routes:
                if document.get('routes_completed') is False:
                    active_routes.append(document)
            # Filter routes
            filtered_data = []
            for routes in active_routes:
                filtered_routes = {}

                for key, value in routes.items():
                    if key not in ('user_firebase_id', 'email', 'days', 'distance_limit', 'duration_limit', 'preferences', 'avoid_tolls', 'routes_completed', 'date_of_completion', 'generation_date', 'routes_id', 'name') and (not value.get('completed', False)):
                        filtered_routes[key] = value

                filtered_routes['user_firebase_id'] = routes['user_firebase_id']
                filtered_routes['email'] = routes['email']
                filtered_routes['days'] = routes['days']
                filtered_routes['distance_limit'] = routes['distance_limit']
                filtered_routes['duration_limit'] = routes['duration_limit']
                filtered_routes['preferences'] = routes['preferences']
                filtered_routes['avoid_tolls'] = routes['avoid_tolls']
                filtered_routes['routes_completed'] = routes['routes_completed']
                filtered_routes['date_of_completion'] = routes['date_of_completion']
                filtered_routes['generation_date'] = routes['generation_date']
                filtered_routes['name'] = routes['name']
                filtered_routes['routes_id'] = routes['routes_id']

                filtered_data.append(filtered_routes)

            filtered_data_to_dict = {str(i): value for i, value in enumerate(filtered_data)}

            if for_stats is True:
                return filtered_data_to_dict

            transformed_document = self.transform_format(filtered_data_to_dict, True)

            return transformed_document

        # Returns all routes no matter if completed is False or True
        all_routes_as_dict = {str(i): value for i, value in enumerate(all_routes)}

        if for_stats is True:
            return all_routes_as_dict

        transformed_document = self.transform_format(all_routes_as_dict, True)

        return transformed_document

    def delete_user_route(self, uid) -> int:
        resp = self.routes_collection.delete_many({"user_firebase_id": uid})
        return resp.deleted_count

    def update_waypoint(self, routes_id: str, route_number: str, location_number: int, visited: bool, should_keep: bool):
        # Get right routes document
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        if routes is None:
            raise HTTPException(status_code=404, detail="Routes not found")
        avoid_tolls = routes['avoid_tolls']
        route = []
        for key, value in routes.items():
            if isinstance(value, dict):
                if 'route_number' in value and value['route_number'] == route_number:
                    route.append((key, value))

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'route_number' in item and item['route_number'] == route_number:
                        route.append((key, item))

        # Check if there is that route in document
        if len(route) == 0:
            raise HTTPException(status_code=404, detail="Route not found")

        # Check if these routes are already completed
        if all(route.get('completed', True) for _, route in routes.items() if isinstance(route, dict)):
            raise HTTPException(status_code=404, detail="Routes already completed")

        # Check if that route is already completed
        if all(item['visited'] in [True, False] for item in route[0][1]['coords']):
            raise HTTPException(status_code=404, detail="Route already completed")

        depot_address = None
        name = None

        # Pass visited into right route
        visited_changed = False
        for key, value in dict(route).items():
            if isinstance(value, dict):
                if 'coords' in value and isinstance(value['coords'], list):
                    for item in value['coords']:
                        if item['isDepot'] is True:
                            depot_address = item['name']
                        if 'location_number' in item and item['location_number'] == location_number:
                            if item['visited'] is not None:
                                raise HTTPException(status_code=404, detail="Location already marked")
                            item['visited'] = visited
                            name = item['name']
                            visited_changed = True
                            if visited is False and should_keep is True and item['isDepot'] is False:
                                self.add_location_to_collection(routes_id, depot_address, item['name'], item['priority'], routes['days'], routes['distance_limit'], routes['duration_limit'], routes['preferences'], routes['avoid_tolls'])
                                item['should_keep'] = True

        # Check if location is in route
        if visited_changed is False:
            raise HTTPException(status_code=404, detail="No such location in route")

        # Check if in all location there is True or False value
        all_visited = all(item['visited'] in [True, False] for item in route[0][1]['coords'])
        route[0][1]['completed'] = all_visited
        current_datetime = datetime.datetime.now()
        if route[0][1]['completed'] is True:
            route[0][1]['date_of_completion'] = f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}'
            real_distance, real_duration, real_polyline, real_fuel = self.get_real_stats(route[0][1]['coords'], avoid_tolls)
            route[0][1]['distance_km'] = real_distance
            route[0][1]['duration_hours'] = real_duration / 60
            route[0][1]['polyline'] = real_polyline
            route[0][1]['fuel_liters'] = real_fuel

        # Update document in mongo
        self.routes_collection.replace_one({"_id": ObjectId(routes_id)}, routes)

        # Update 'routes_completed' if all routes are completed
        all_routes_completed = all(route.get('completed', True) for _, route in routes.items() if isinstance(route, dict))
        if all_routes_completed:
            self.routes_collection.update_one({'_id': ObjectId(routes_id)}, {'$set': {'routes_completed': True, 'date_of_completion': f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}'}})

        if name == depot_address:
            return {'routes_id': routes_id,
                    'route_number': route_number,
                    'name': name,
                    'location_number': location_number,
                    'visited': visited,
                    'completed': all_visited,
                    'date_of_completion': route[0][1]['date_of_completion'],
                    'routes_completed': all_routes_completed}

        return {'routes_id': routes_id,
                'route_number': route_number,
                'name': name,
                'location_number': location_number,
                'visited': visited,
                'should_keep': should_keep,
                'completed': all_visited,
                'date_of_completion': route[0][1]['date_of_completion'],
                'routes_completed': all_routes_completed}

    def add_location_to_collection(self, routes_id, depot_address, address, priority, days, distance_limit, duration_limit, preferences, avoid_tolls):
        # Check if there is a document with that routes
        routes = self.locations_collection.find_one({"routes_id": routes_id})
        if routes is None:
            # Create document for routes_id
            document = {'depot_address': depot_address,
                        'addresses': [address],
                        'priorities': [priority],
                        'days': days,
                        'distance_limit': distance_limit,
                        'duration_limit': duration_limit,
                        'preferences': preferences,
                        'avoid_tolls': avoid_tolls,
                        'routes_id': routes_id}

            res = self.locations_collection.insert_one(document)

        else:
            # Update document
            document = {'depot_address': routes['depot_address'],
                        'addresses': routes['addresses'] + [address],
                        'priorities': routes['priorities'] + [priority],
                        'days': routes['days'],
                        'distance_limit': routes['distance_limit'],
                        'duration_limit': routes['duration_limit'],
                        'preferences': routes['preferences'],
                        'avoid_tolls': routes['avoid_tolls'],
                        'routes_id': routes['routes_id']}

            res = self.locations_collection.replace_one({"routes_id": routes_id}, document)

    def get_locations_to_regenerate(self, routes_id):
        #Get locations that were sent to be revisited
        locations = self.locations_collection.find_one({"routes_id": routes_id})
        if locations is not None:
            depot_address_locations = locations['depot_address']
            addresses_locations = locations['addresses']
            priorities_locations = locations['priorities']
            days_locations = locations['days']
            distance_limit_locations = locations['distance_limit']
            duration_limit_locations = locations['duration_limit']
            preferences_locations = locations['preferences']
            avoid_tolls_locations = locations['avoid_tolls']
            self.locations_collection.delete_many({"routes_id": routes_id})

        #Get routes that were not visited
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        if routes is not None:
            depot_address_routes = None
            addresses_routes = []
            priorities_routes = []
            days_routes = None
            distance_limit_routes = None
            duration_limit_routes = None
            preferences_routes = None
            avoid_tolls_routes = None
            for key, value in routes.items():
                if isinstance(value, dict):
                    if value['completed'] is False:
                        for item in value['coords']:
                            if item['isDepot'] is True:
                                depot_address_routes = item['name']
                            if item['isDepot'] is False:
                                addresses_routes.append(item['name'])
                                priorities_routes.append(item['priority'])
                if key == 'days':
                    days_routes = value
                if key == 'distance_limit':
                    distance_limit_routes = value
                if key == 'duration_limit':
                    duration_limit_routes = value
                if key == 'preferences':
                    preferences_routes = value
                if key == 'avoid_tolls':
                    avoid_tolls_routes = value

        #Combine
        if locations is None and routes is None:
            return{'message': 'No locations to regenerate'}
        if locations is not None and routes is None:
            document = {'depot_address': depot_address_locations,
                        'addresses': addresses_locations,
                        'priorities': priorities_locations,
                        'days': days_locations,
                        'distance_limit': distance_limit_locations,
                        'duration_limit': duration_limit_locations,
                        'preferences': preferences_locations,
                        'avoid_tolls': avoid_tolls_locations,
                        'routes_id': routes_id}
            return document
        if locations is None and routes is not None:
            document = {'depot_address': depot_address_routes,
                        'addresses': addresses_routes,
                        'priorities': priorities_routes,
                        'days': days_routes,
                        'distance_limit': distance_limit_routes,
                        'duration_limit': duration_limit_routes,
                        'preferences': preferences_routes,
                        'avoid_tolls': avoid_tolls_routes,
                        'routes_id': routes_id}
            return document
        if locations is not None and routes is not None:
            document = {'depot_address': depot_address_locations,
                        'addresses': addresses_locations + addresses_routes,
                        'priorities': priorities_locations + priorities_routes,
                        'days': days_locations,
                        'distance_limit': distance_limit_locations,
                        'duration_limit': duration_limit_locations,
                        'preferences': preferences_locations,
                        'avoid_tolls': avoid_tolls_locations,
                        'routes_id': routes_id}
            return document

    def get_real_stats(self, route, avoid_tolls):
        locations = []
        for location in route:
            if location['isDepot'] is True:
                locations.append([location['latitude'], location['longitude']])
            if location['visited'] is True and location['isDepot'] is False:
                locations.append([location['latitude'], location['longitude']])

        if len(locations) == 2:
            return 0.0, 0.0, "", 0.0

        real_distance, real_duration, real_polyline, poly = routes_planner.get_distance_duration(avoid_tolls, locations)

        real_total_fuel = 0
        for i in range(len(locations) - 1):
            origin = locations[i]
            destination = locations[i + 1]
            fuel_consumption = routes_planner.get_fuel_between_points(avoid_tolls, origin, destination)
            real_total_fuel = real_total_fuel + fuel_consumption

        return real_distance, real_duration, real_polyline, real_total_fuel

    def collect_stats(self, uid, start_date, end_date):
        routes = self.get_user_route(uid, False, True)
        num_completed_routes = 0
        sum_distance = 0
        sum_duration = 0
        sum_fuel = 0
        sum_days_of_week = {'Monday':0, 'Tuesday':0, 'Wednesday': 0, 'Thursday':0, 'Friday':0, 'Saturday':0, 'Sunday': 0}
        num_visited_loc = 0
        num_unvisited_loc = 0
        most_frequently_visited = []
        most_frequently_missed = []
        sum_of_priorities = {'Priority 1':0, 'Priority 2':0, 'Priority 3':0}
        most_frequent_depot = []
        for key, value in routes.items():
            if isinstance(value, dict):
                for key_in, value_in in value.items():
                    if isinstance(value_in, dict):
                        if value_in['date_of_completion'] is not None and parse(start_date) <= parse(value_in['date_of_completion']) <= parse(end_date):
                            num_completed_routes = num_completed_routes + 1
                            sum_distance = sum_distance + value_in['distance_km']
                            sum_duration = sum_duration + value_in['duration_hours']
                            sum_fuel = sum_fuel + value_in['fuel_liters']
                            data_obj = parse(value_in['date_of_completion'])
                            day_of_week = data_obj.strftime("%A")
                            sum_days_of_week[day_of_week] = sum_days_of_week[day_of_week] + 1
                            for location in value_in['coords']:
                                if location['visited'] is True and location['isDepot'] is False:
                                    num_visited_loc = num_visited_loc + 1
                                    most_frequently_visited.append(location['name'])
                                    if location['priority'] == 1:
                                        sum_of_priorities['Priority 1'] = sum_of_priorities['Priority 1'] + 1
                                    if location['priority'] == 2:
                                        sum_of_priorities['Priority 2'] = sum_of_priorities['Priority 2'] + 1
                                    if location['priority'] == 3:
                                        sum_of_priorities['Priority 3'] = sum_of_priorities['Priority 3'] + 1
                                if location['visited'] is False and location['isDepot'] is False:
                                    num_unvisited_loc = num_unvisited_loc + 1
                                    most_frequently_missed.append(location['name'])
                                if location['isDepot'] is True:
                                    most_frequent_depot.append(location['name'])

        return {'number_of_completed_routes': num_completed_routes,
                'summed_distance_km': sum_distance,
                'summed_duration_hours' : sum_duration,
                'summed_fuel_liters': sum_fuel,
                'summed_days_of_week_to_complete': sum_days_of_week,
                'number_of_visited_locations': num_visited_loc,
                'number_of_unvisited_locations': num_unvisited_loc,
                'most_frequently_visited_locations': self.get_most_popular(most_frequently_visited),
                'most_frequently_missed_locations': self.get_most_popular(most_frequently_missed),
                'summed_visited_priorities': sum_of_priorities,
                'most_frequent_depot': self.get_most_popular(most_frequent_depot, divide=True)}

    def get_most_popular(self, locations, divide=False):
        locations_with_count = {}
        for location in locations:
            if location in locations_with_count:
                locations_with_count[location] += 1
            else:
                locations_with_count[location] = 1

        for location, count in locations_with_count.items():
            locations_with_count[location] = count // 2 if divide is True else count

        sorted_counts = sorted(locations_with_count.items(), key=lambda x: x[1])
        least_popular = sorted_counts[:3]
        most_popular = sorted_counts[-3:][::-1]

        result = [{"address": address, "count": count} for address, count in most_popular]

        return result

    def change_routes_name(self, routes_id, name):
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        if routes is None:
            raise HTTPException(status_code=404, detail="Routes not found")
        self.routes_collection.update_one({'_id': ObjectId(routes_id)}, {'$set': {'name': name}})
        return {
            "routes_id": str(routes['_id']),
            "name": name
        }

