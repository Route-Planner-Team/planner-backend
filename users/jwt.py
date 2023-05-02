import jwt
from config import Config
from datetime import datetime, timedelta
from fastapi.exceptions import HTTPException
from jwt.exceptions import *

class JWTAuth:
    @staticmethod
    def authenticate(headers):
        """
        return (user, token) or raise Exception if authed. failed
        """
        try:
            token = headers.split(" ")
            payload = jwt.decode(token[1], Config.JWTKEY, algorithms=['HS256'])
            # email = payload['_id']
            return payload

        except ExpiredSignatureError:
            # token can be invalid, np. expired
            raise ExpiredSignatureError
        except KeyError:
            # we don't have Authorization in Headers key or don't have token -> return None
            raise KeyError
        except DecodeError:
            raise DecodeError