from datetime import datetime
from typing import Optional

from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult
from fastapi_exceptions.exceptions import NotAuthenticated
from fastapi import HTTPException
from passlib.context import CryptContext
from pyisemail import is_email

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserModel(BaseModel):
    email: str
    password: str
    # created_at: Optional[str] = datetime.now().isoformat()

class UserRepository:
    def __init__(self, config):
        self.config = config
        self.client: MongoClient = MongoClient(self.config.MONGO)
        self.db: Database = self.client.route_db
        self.users_collection: Collection = self.client.route_db.users
        logger.info("Inited repo")

    def create_user(self, body: dict) -> dict:
        """
        Create user's document in mongoDB
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"
        :return: dict
        """

        if not is_email(body['email']):
            raise HTTPException(status_code=404, detail="Invalid email")

        if self.users_collection.find_one({"email": body['email']}):
            raise HTTPException(status_code=404, detail="User with this email already exists")

        hashed_password = pwd_context.hash(body['password'])
        body['password'] = hashed_password

        user: InsertOneResult = self.users_collection.insert_one(body)
        new_user = self.users_collection.find_one({"_id": user.inserted_id})

        resp = {
            "_id": str(new_user['_id']),
            "email": new_user['email'],
            "password": new_user['password']
            # "created_at": new_user['created_at']
        }
        logger.info(f"Create new user {resp}")
        return resp

    def get_user(self, body: dict) -> dict:
        """
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"
        :return: dict
        """

        if not self.users_collection.find_one({"email": body['email']}):
            raise HTTPException(status_code=404, detail="No user with that email address")

        user = self.users_collection.find_one({"email": body['email']})
        try:
            if pwd_context.verify(body['password'], user['password']):
                resp = {
                    "_id": str(user['_id']),
                    "email": user['email'],
                    "password": user['password']
                    # "created_at": new_user['created_at']
                }
                return resp
            raise NotAuthenticated
        except KeyError:
            raise KeyError
