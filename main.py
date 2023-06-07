import sys

import firebase_admin
import googlemaps
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_exceptions.exceptions import NotAuthenticated
from firebase_admin import credentials
from loguru import logger

from config import Config
from routes.model import RoutesModel, WaypointModel
from routes.planner import RoutesPlanner
from routes.route_repository import RouteRepository
from users.auth import authenticate_header
from users.model import UserEmailModel, UserModel, UserModelChangePassword
from users.user_repository import UserRepository

cfg = Config()

user_repo = UserRepository(cfg)
routes_repo = RouteRepository(cfg)

routes_planner = RoutesPlanner(cfg)

cred = credentials.Certificate({
    "type": Config.FIREBASE_TYPE,
    "project_id": Config.FIREBASE_PROJECT_ID,
    "private_key_id": Config.FIREBASE_PRIVATE_KEY_ID,
    "private_key": Config.FIREBASE_PRIVATE_KEY,
    "client_email": Config.FIREBASE_CLIENT_EMAIL,
    "client_id": Config.FIREBASE_CLIENT_ID,
    "auth_uri": Config.FIREBASE_AUTH_URI,
    "token_uri": Config.FIREBASE_TOKEN_URI,
    "auth_provider_x509_cert_url": Config.FIREBASE_AUTH_PROVIDER_X509_CERT_URL,
    "client_x509_cert_url": Config.FIREBASE_CLIENT_X509_CERT_URL

})
firebase = firebase_admin.initialize_app(cred)

gmaps = googlemaps.Client(key=Config.GOOGLEMAPS_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

'''
To get authorization token:
In postman -> POST https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=<FIREBASE_API_KEY> (from env)
body as json -> {"email":"test@wp.pl","password":"test123","returnSecureToken":true}
u will get "idToken"

copy idToken and put into any request in Headers (key: Authorization, Value: Bearer <idToken>
'''

def change_key_name(dictionary, old_key, new_key):
    if old_key in dictionary:
        dictionary[new_key] = dictionary.pop(old_key)

@app.middleware("http")
def firebase_middleware(request: Request, call_next):
    return authenticate_header(request, call_next) # type: ignore


@app.get("/")
def ping():
    return {"message": "pong"}


@app.post("/auth/sign-up")
@logger.catch
def create_user(user: UserModel, status_code=201):
    """
    Handler to create user
    """

    status = user_repo.create_user(user.dict())

    return status


@app.post("/auth/sign-in")
@logger.catch
def login_user(user: UserModel):
    """
    Sign-in handler
    """
    try:
        firebase_payload = user_repo.get_user(user.dict())
        del firebase_payload['kind']
        del firebase_payload['localId']
        del firebase_payload['displayName']
        del firebase_payload['registered']

        change_key_name(firebase_payload, "expiresIn", "expires_in")
        change_key_name(firebase_payload, "idToken", "access_token")
        change_key_name(firebase_payload, "refreshToken", "refresh_token")

        return firebase_payload

    except NotAuthenticated:
        return {"Message": "Auth failed!"}


@app.post("/auth/change-password")
@logger.catch
def change_password(request: Request, user: UserModelChangePassword):
    """
    Handler to change password for logged in user
    """

    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    status = user_repo.change_password(uid, user.dict())
    data ={
        "user_firebase_id": status._data["localId"],
        "email": status._data["email"],
        "password_updated_at": status._data["passwordUpdatedAt"]
    }
    return data


@app.post("/auth/forgot-password")
@logger.catch
def forgot_password(user: UserEmailModel):
    """
    Handler to change password for not logged in user
    """

    status = user_repo.forgot_password(user.dict())
    return status


@app.get("/routes")
@logger.catch
def routes_get_handler(request: Request):
    """Return all routes for current user
    Raises:
        NotAuthenticated
    Returns:
        all routes for current user
    """

    uid = request.state.uid
    if uid is None :
        raise NotAuthenticated('User ID not found in token')

    res = routes_repo.get_user_route(uid=uid)

    return {"Result": res}


@app.post("/routes")
@logger.catch
def routes_post_handler(request: Request, routes: RoutesModel):
    uid = request.state.uid
    try:
        routes = routes_planner.get_routes(routes.depot_address,
                                           routes.addresses,
                                           routes.priorities,
                                           routes.days,
                                           routes.distance_limit,
                                           routes.duration_limit,
                                           routes.preferences,
                                           routes.avoid_tolls)
        routes = routes_repo.create_user_route(uid, routes)

    except ValueError as e:
        error = str(e)
        return JSONResponse(status_code=400, content={"error": error})


    return routes

@app.delete("/routes")
@logger.catch
def del_user_route(request: Request):
    """Delete all routes for current user
    Raises:
        NotAuthenticated

    Returns:
        Deleted int
    """

    uid = request.state.uid
    if uid is None :
        raise NotAuthenticated('User ID not found in token')
    count = routes_repo.delete_user_route(uid=uid)
    return {"Deleted": count}


@app.get("/routes/active")
@logger.catch
def active_routes_handler(request: Request):
    """
    Return all routes for current user, where visited is false (active routes to visit)
    """

    uid = request.state.uid
    if uid is None :
        raise NotAuthenticated('User ID not found in token')

    res = routes_repo.get_user_route(uid=uid, active=True)
    return {"Result": res}


@app.post("/routes/waypoint")
@logger.catch
def mark_visited_waypoint(request: Request, waypoint: WaypointModel):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        updated_waypoint = routes_repo.update_waypoint(waypoint._id,
                                             waypoint.route_id,
                                             waypoint.location_number,
                                             waypoint.visited,
                                             waypoint.comment)

        return updated_waypoint

    except ValueError as e:
        error = str(e)
        print(error, file=sys.stderr)
        return JSONResponse(status_code=400, content={"error": error})