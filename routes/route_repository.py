from bson.objectid import ObjectId
from loguru import logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from passlib.context import CryptContext
from firebase_admin import credentials, auth
from pymongo.results import InsertOneResult
import json
from bson import json_util


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
        r = self.convert_dict_keys_to_str(body)

        r['user_firebase_id'] = uid
        firebase_user = auth.get_user(uid)

        r['email'] = firebase_user.email

        res = self.routes_collection.insert_one(dict(r))

        r['routes_id'] = str(res.inserted_id)

        return r

    def get_user_route(self, uid: str):
        firebase_user = auth.get_user(uid)
        resp = self.routes_collection.find({"email": firebase_user.email})
        r = []
        for doc in resp:
            if '_id' in doc:
                doc['routes_id'] = doc.pop('_id')
            r.append(str(doc))

        return r

    def delete_user_route(self, uid) -> int:
        firebase_user = auth.get_user(uid)
        resp = self.routes_collection.delete_many({"email": firebase_user.email})
        return resp.deleted_count

    def update_waypoint(self, routes_id: str, route_id: str, location_number: int, visited: bool, comment: str):
        # Get right routes document
        routes = self.routes_collection.find_one({"_id": ObjectId(routes_id)})
        route = []
        for key, value in routes.items():
            if isinstance(value, dict):
                if 'route_id' in value and value['route_id'] == route_id:
                    route.append((key, value))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and 'route_id' in item and item['route_id'] == route_id:
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

        return {'routes_id': routes_id, 'route_id': route_id, 'location_number': location_number, 'visited': visited, 'comment': comment, 'whole_route_completed': all_visited}
