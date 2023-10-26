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
        current_datetime = datetime.datetime.now()
        document['generation_date'] = f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}'

        if routes_id is not None:
            routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
            if routes is not None:
                completed_routes = self.get_completed_routes(routes)
                document, new_days = self.merge_routes(document, completed_routes)
                document['days'] = new_days
                self.routes_collection.replace_one({"_id": ObjectId(routes_id)}, document)
                document['routes_id'] = str(routes_id)
                return document

        res = self.routes_collection.insert_one(dict(document))

        document['routes_id'] = str(res.inserted_id)

        return document

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

    def get_user_route(self, uid: str, active=False):
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
                    if key not in ('user_firebase_id', 'email', 'days', 'distance_limit', 'duration_limit', 'preferences', 'avoid_tolls', 'routes_completed', 'generation_date', 'routes_id') and (not value.get('completed', False)):
                        filtered_routes[key] = value

                filtered_routes['user_firebase_id'] = routes['user_firebase_id']
                filtered_routes['email'] = routes['email']
                filtered_routes['days'] = routes['days']
                filtered_routes['distance_limit'] = routes['distance_limit']
                filtered_routes['duration_limit'] = routes['duration_limit']
                filtered_routes['preferences'] = routes['preferences']
                filtered_routes['avoid_tolls'] = routes['avoid_tolls']
                filtered_routes['routes_completed'] = routes['routes_completed']
                filtered_routes['generation_date'] = routes['generation_date']
                filtered_routes['routes_id'] = routes['routes_id']

                filtered_data.append(filtered_routes)

            filtered_data_to_dict = {str(i): value for i, value in enumerate(filtered_data)}

            return filtered_data_to_dict

        # Returns all routes no matter if completed is False or True
        all_routes_as_dict = {str(i): value for i, value in enumerate(all_routes)}

        return all_routes_as_dict

    def delete_user_route(self, uid) -> int:
        resp = self.routes_collection.delete_many({"user_firebase_id": uid})
        return resp.deleted_count

    def update_waypoint(self, routes_id: str, route_number: str, location_number: int, visited: bool, should_keep: bool):
        # Get right routes document
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        if routes is None:
            raise HTTPException(status_code=404, detail="Routes not found")
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

            # TODO, calculate real consumption for stats

        # Update document in mongo
        self.routes_collection.replace_one({"_id": ObjectId(routes_id)}, routes)

        # Update 'routes_completed' if all routes are completed
        all_routes_completed = all(route.get('completed', True) for _, route in routes.items() if isinstance(route, dict))
        if all_routes_completed:
            self.routes_collection.update_one({'_id': ObjectId(routes_id)}, {'$set': {'routes_completed': True}})

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
