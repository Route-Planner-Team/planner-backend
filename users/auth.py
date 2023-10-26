import jwt
from config import Config
from datetime import datetime, timedelta
from fastapi.exceptions import HTTPException
from jwt.exceptions import *
from fastapi import HTTPException, Request, Depends
from fastapi_exceptions.exceptions import NotAuthenticated
from firebase_admin import auth

protected_endpoints = [
    "/auth/change-password",
    "/routes",
    "/routes/active",
    "/routes/waypoint"
    "/routes/regenerate",
    "/stats"
    ]  # add endpoints you want to authorize

def authenticate_header(request: Request, call_next):
    """
    :param request, call_next:
    :return verify authentication or raise an error:
    """
    if any(request.url.path.startswith(endpoint) for endpoint in protected_endpoints):
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                raise NotAuthenticated('Authorization header not found')
            auth_token = auth_header.split(" ")[1]
            decoded_token = auth.verify_id_token(auth_token)
            request.state.uid = decoded_token['uid']
        except Exception as e:
            raise NotAuthenticated(str(e))
        response = call_next(request)
        return response
    else:
        response = call_next(request)
        return response
