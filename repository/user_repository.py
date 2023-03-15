from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult

from config import Config


class UserModel(BaseModel):
    email: str
    password: str
    created_at: Optional[str] = datetime.now().isoformat()


class UserRepository:
    def __init__(self, config: Config):
        self.config = config
        self.client: MongoClient = MongoClient(self.config.mongo_conn)
        self.db: Database = self.client.route_db
        self.users_collection: Collection = self.client.route_db.users
        logger.info("Inited repo")

    def create_user(self, body: dict) -> dict:
        """
        Create user's document in mongoDB
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"
        :return: dict
        """

        user: InsertOneResult = self.users_collection.insert_one(body)
        new_user = self.users_collection.find_one({"_id": user.inserted_id})

        resp = {
            # "_id": str(new_user['_id']),
            "email": new_user['email'],
            # "password": new_user['password'],
            "created_at": new_user['created_at']
        }
        logger.info(f"Create new user {resp}")
        return resp

    def get_user(self, email: str, password: str) -> bool:
        """
        Check if password in param equal to password in db for user email
        :param email: str
        :param password: str
        :return: bool
        """

        user = self.users_collection.find_one({"email": email})
        try:
            if user['password'] == password:
                return True
            return False
        except KeyError:
            return False

