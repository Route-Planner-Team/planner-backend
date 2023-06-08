from bson import json_util
from bson.objectid import ObjectId
from firebase_admin import auth, credentials
from loguru import logger
from passlib.context import CryptContext
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult


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

        all_docs = {}

        for key, value in document.items():
            value['user_firebase_id'] = uid
            value['email'] = firebase_user.email
            res = self.routes_collection.insert_one(dict(value))
            value['route_id'] = str(res.inserted_id)
            all_docs[key] = value

        return all_docs

    def get_user_route(self, uid: str, active=False):
        cursor = self.routes_collection.find({"user_firebase_id": uid})
        documents = list(cursor)

        all_routes = []

        for document in documents:
            document['route_id'] = str(document.pop('_id'))
            all_routes.append(document)

        # Returns routes where completed is False
        if active is True:
            active_routes = {str(i): value for i, value in enumerate(all_routes) if value.get('completed') is False}
            active_routes = {str(i): value for i, (key, value) in enumerate(active_routes.items())}
            return active_routes

        all_routes_as_dict = {str(i): value for i, value in enumerate(all_routes)}

        # Returns all routes no matter if completed is False or True
        return all_routes_as_dict

    def delete_user_route(self, uid) -> int:
        resp = self.routes_collection.delete_many({"user_firebase_id": uid})
        return resp.deleted_count

    def update_waypoint(self, route_id: str, location_number: int, visited: bool, comment: str):
        # Get right routes document
        route = self.routes_collection.find_one({"_id": ObjectId(route_id)})

        # Pass visited and comment into route
        if 'coords' in route and isinstance(route['coords'], list):
            for item in route['coords']:
                if 'location_number' in item and item['location_number'] == location_number:
                    item['visited'] = visited
                    item['comment'] = comment

        # Check if in all location there is True or False value
        all_visited = all(item['visited'] in [True, False] for item in route['coords'])
        route['completed'] = all_visited

        # Update document in mongo
        self.routes_collection.replace_one({"_id": ObjectId(route_id)}, route)

        return {'route_id': route_id,
                'location_number': location_number,
                'visited': visited,
                'comment': comment,
                'whole_route_completed': all_visited}
