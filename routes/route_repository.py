from bson.objectid import ObjectId
from loguru import logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from passlib.context import CryptContext
from firebase_admin import credentials, auth
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
        r = self.convert_dict_keys_to_str(body)
        r['user_firebase_id'] = uid
        firebase_user = auth.get_user(uid)
        r['email'] = firebase_user.email
        res = self.routes_collection.insert_one(dict(r))
        return r

    def get_user_route(self, uid: str):
        firebase_user = auth.get_user(uid)
        resp = self.routes_collection.find({"email": firebase_user.email})
        r = []
        for doc in resp:
            if '_id' in doc:
                doc['route_id'] = doc.pop('_id')
            r.append(str(doc))

        return r

    def delete_user_route(self, uid) -> int:
        firebase_user = auth.get_user(uid)
        resp = self.routes_collection.delete_many({"email": firebase_user.email})
        return resp.deleted_count

    def mark_route_points(self, uid, body: dict):
        firebase_user = auth.get_user(uid)
        resp = self.visited_collection.insert_one(body)
        return str(resp.inserted_id)