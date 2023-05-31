from datetime import datetime
from typing import Optional

import requests
from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.results import InsertOneResult
from fastapi_exceptions.exceptions import NotAuthenticated
from fastapi import HTTPException, Request, Depends
from passlib.context import CryptContext
from firebase_admin import credentials, auth
import json
import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"}
        :return: dict
        """

        # if self.users_collection.find_one({"email": body['email']}):
        #     raise HTTPException(status_code=404, detail="User with this email already exists")

        firebase_user = auth.create_user(
            email=body['email'],
            password=body['password']
        )

        body['user_firebase_id'] = firebase_user.uid
        del body['password']

        user: InsertOneResult = self.users_collection.insert_one(body)
        new_user = self.users_collection.find_one({"_id": user.inserted_id})

        resp = {
            "user_mongo_id": str(new_user['_id']),
            "email": new_user['email'],
            "user_firebase_id": new_user['user_firebase_id']
        }
        logger.info(f"Create new user {resp}")
        return resp

    def get_user(self, body: dict) -> dict:
        """
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"}
        :return: dict
        """

        if not self.users_collection.find_one({"email": body['email']}):
            raise HTTPException(status_code=404, detail="No user with that email address")

        firebase_user = auth.get_user_by_email(body['email'])

        user = self.users_collection.find_one({"email": body['email']})

        if user['user_firebase_id'] != firebase_user.uid:
            raise ValueError('Firebase UID does not match MongoDB UID')

        rest_api_url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={config.Config.FIREBASE_API_KEY}"
        payload = json.dumps({
            'email': body['email'],
            'password': body['password'],
            "returnSecureToken": True
        })

        r = requests.post(rest_api_url,data=payload)

        response = r.json()

        if 'error' in response:
            error_message = response['error']['message']
            if error_message == 'INVALID_PASSWORD':
                raise ValueError('Invalid password')
            else:
                raise ValueError('An error occurred during authentication')

        return response

    def change_password(self, uid, body: dict) -> dict:
        """
        :param uid:
        :param body: example {"new_password": "test123!", "confirm_new_password": "test123!"}
        :return: dict
        """

        firebase_user = auth.get_user(uid)

        if body['new_password'] != body['confirm_new_password']:
            raise ValueError("Passed passwords are not identical.")
        else:
            updated_firebase_user = auth.update_user(firebase_user.uid, password=body['new_password'])

        return updated_firebase_user

    def forgot_password(self, body: dict) -> dict:
        """
        :param body: example {"email": "abc@gmail.com"}
        :return: dict
        """

        if not self.users_collection.find_one({"email": body['email']}):
            raise HTTPException(status_code=404, detail="No user with that email address")

        rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
        data = {"requestType": "PASSWORD_RESET", "email": body['email']}

        r = requests.post(rest_api_url,
                          params={'key': config.Config.FIREBASE_API_KEY},
                          data=data)

        return r.json()
