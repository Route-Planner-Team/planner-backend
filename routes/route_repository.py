from bson.objectid import ObjectId
from loguru import logger
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


    def create_user_route(self,  email: str, body: dict):
        r=self.convert_dict_keys_to_str(body)
        r["email"]=  email
        res = self.routes_collection.insert_one(dict(r))
        return r

    def get_route_by_user_email(self, email):
        resp = self.routes_collection.find({"email": email})
        r = []
        for doc in resp:
            del doc['_id']
            r.append(doc)
        return r