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
        self.routes_collection: Collection = self.client.route_db.routes
        self.locations_collection: Collection = self.client.route_db.locations
        logger.info("Inited repo")

    def create_user(self, body: dict) -> dict:
        """
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"}
        :return: dict
        """

        firebase_user = auth.create_user(
            email=body['email'],
            password=body['password']
        )

        resp = {
            "email": firebase_user.email,
            "user_firebase_id": firebase_user.uid
        }
        logger.info(f"Create new user {resp}")
        return resp

    def get_user(self, body: dict) -> dict:
        """
        :param body: example {"email": "abc@gmail.com", "password": "qwe123"}
        :return: dict
        """

        firebase_request_url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={config.Config.FIREBASE_API_KEY}"
        payload = json.dumps({
            'email': body['email'],
            'password': body['password'],
            "returnSecureToken": True
        })

        r = requests.post(firebase_request_url,data=payload)

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

        rest_api_url = "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode"
        data = {"requestType": "PASSWORD_RESET", "email": body['email']}

        r = requests.post(rest_api_url,
                          params={'key': config.Config.FIREBASE_API_KEY},
                          data=data)

        response = r.json()

        if 'error' in response:
            error_message = response['error']['message']
            if error_message == 'EMAIL_NOT_FOUND':
                raise ValueError('Email not found')
            else:
                raise ValueError('An error occurred')

        return r.json()

    def delete_user(self, uid):
        try:
            status = auth.delete_user(uid)
            routes_resp = self.routes_collection.delete_many({"user_firebase_id": uid})
            locations_resp = self.locations_collection.delete_many({'user_firebase_id': uid})
            return {'message': 'User has been deleted'}

        except auth.UserNotFoundError:
            logger.error("User not found")
            return {'error': 'User not found'}

        except Exception as e:
            logger.error(f"Error deleting user for UID {uid}: {str(e)}")
            return {'error': str(e)}

    def change_email(self, uid, email):
        try:
            user = auth.get_user(uid)
            if user.email == email:
                return {'message': 'Provide new email'}
            status = auth.update_user(uid, email=email)
            routes_resp = self.routes_collection.update_many({'user_firebase_id': user.uid}, {'$set': {'email': email}})
            return {'message': 'Email changed successfully'}

        except auth.UserNotFoundError:
            logger.error("User not found")
            return {'error': 'User not found'}

        except Exception as e:
            logger.error("An error occured")
            return {'error': str(e)}