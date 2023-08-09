from bson import json_util
from bson.objectid import ObjectId
from firebase_admin import auth, credentials
from loguru import logger
from passlib.context import CryptContext
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult

import datetime


class RouteRepository():
    def __init__(self, config):
        self.config = config
        self.client: MongoClient = MongoClient(self.config.MONGO)
        self.db: Database = self.client.route_db
        self.routes_collection: Collection = self.client.route_db.routes
        self.visited_collection: Collection = self.client.route_db.visited_points
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

    def create_user_route(self, uid: str, body: dict):
        firebase_user = auth.get_user(uid)

        document = self.convert_dict_keys_to_str(body)

        document['user_firebase_id'] = uid
        document['email'] = firebase_user.email

        document['routes_completed'] = False

        current_datetime = datetime.datetime.now()
        document['generation_date'] = f'{current_datetime.day:02d}.{current_datetime.month:02d}.{current_datetime.year}, {current_datetime.hour:02d}:{current_datetime.minute:02d}'

        res = self.routes_collection.insert_one(dict(document))

        document['routes_id'] = str(res.inserted_id)

        return document
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
                    if key not in ('user_firebase_id', 'email', 'routes_completed', 'generation_date', 'routes_id') and (not value.get('completed', False)):
                        filtered_routes[key] = value

                filtered_routes['user_firebase_id'] = routes['user_firebase_id']
                filtered_routes['email'] = routes['email']
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

    def update_waypoint(self, routes_id: str, route_number: str, location_number: int, visited: bool, comment: str):
        # Get right routes document
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        route = []
        for key, value in routes.items():
            if isinstance(value, dict):
                if 'route_number' in value and value['route_number'] == route_number:
                    route.append((key, value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'route_number' in item and item['route_number'] == route_number:
                        route.append((key, item))

        # Pass visited and comment into right route
        for key, value in dict(route).items():
            if isinstance(value, dict):
                if 'coords' in value and isinstance(value['coords'], list):
                    for item in value['coords']:
                        if 'location_number' in item and item['location_number'] == location_number:
                            item['visited'] = visited
                            item['comment'] = comment

        # Check if in all location there is True or False value
        all_visited = all(item['visited'] in [True, False] for item in route[0][1]['coords'])
        route[0][1]['completed'] = all_visited

        # Update document in mongo
        self.routes_collection.replace_one({"_id": ObjectId(routes_id)}, routes)

        # Update 'routes_completed' if all routes are completed
        all_routes_completed = all(route.get('completed', True) for _, route in routes.items() if isinstance(route, dict))
        if all_routes_completed:
            self.routes_collection.update_one({'_id': ObjectId(routes_id)}, {'$set': {'routes_completed': True}})

        return {'routes_id': routes_id,
                'route_number': route_number,
                'location_number': location_number,
                'visited': visited,
                'comment': comment,
                'completed': all_visited,
                'routes_completed': all_routes_completed}