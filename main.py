import sys

import firebase_admin
from firebase_admin.auth import EmailAlreadyExistsError
import googlemaps
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_exceptions.exceptions import NotAuthenticated
from firebase_admin import credentials
from fastapi import HTTPException
from loguru import logger

from config import Config
from routes.model import RoutesModel, WaypointModel, RegenerateModel, StatisticModel, RenameModel
from routes.planner import RoutesPlanner
from routes.route_repository import RouteRepository
from users.auth import authenticate_header
from users.model import UserEmailModel, UserModel, UserModelChangePassword
from users.user_repository import UserRepository

from datetime import datetime

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

    try:
        status = user_repo.create_user(user.dict())
        return status
    except EmailAlreadyExistsError as e:
        error_message = str(e)
        return {'error': error_message}


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

    except ValueError as e:
        error_message = str(e)
        return {'error': error_message}

    except NotAuthenticated:
        return {"error": "Auth failed!"}


@app.post("/auth/change-password")
@logger.catch
def change_password(request: Request, user: UserModelChangePassword):
    """
    Handler to change password for logged in user
    """

    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    try:
        status = user_repo.change_password(uid, user.dict())
        data ={
            "user_firebase_id": status._data["localId"],
            "email": status._data["email"],
            "password_updated_at": status._data["passwordUpdatedAt"]
        }
        return data

    except ValueError as e:
        error_message = str(e)
        return {'error': error_message}


@app.post("/auth/forgot-password")
@logger.catch
def forgot_password(user: UserEmailModel):
    """
    Handler to change password for not logged in user
    """

    try:
        status = user_repo.forgot_password(user.dict())
        return status

    except ValueError as e:
        error_message = str(e)
        return {'error': error_message}

@app.post("/auth/delete")
@logger.catch
def delete_user(request: Request):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    try:
        status = user_repo.delete_user(uid)
        return status

    except NotAuthenticated as e:
        logger.error(f"Authentication error: {str(e)}")
        return JSONResponse(status_code=401, content={"error": str(e)})

    except ValueError as e:
        error = str(e)
        logger.error(f"ValueError: {error}")
        return JSONResponse(status_code=400, content={"error": error})

@app.post("/auth/change-email")
@logger.catch
def change_email(request: Request, user: UserEmailModel):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    try:
        status = user_repo.change_email(uid, user.email)
        return status

    except NotAuthenticated as e:
        logger.error(f"Authentication error: {str(e)}")
        return JSONResponse(status_code=401, content={"error": str(e)})

    except ValueError as e:
        error = str(e)
        logger.error(f"ValueError: {error}")
        return JSONResponse(status_code=400, content={"error": error})

@app.get("/routes")
@logger.catch
def routes_get_handler(request: Request):
    """
    Return all routes for current user (completed and uncompleted)
    """

    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    res = routes_repo.get_user_route(uid=uid)

    if len(res['routes']) == 0:
        return {'message': 'No routes for that user'}

    return res


@app.get("/routes/active")
@logger.catch
def active_routes_handler(request: Request):
    """
    Return routes for current user, where completed is false (returns active routes to visit)
    """

    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')

    res = routes_repo.get_user_route(uid=uid, active=True)

    if len(res['routes']) == 0:
        return {'message': 'No active routes for that user'}

    return res


@app.post("/routes")
@logger.catch
def routes_post_handler(request: Request, routes: RoutesModel, routes_id: str = None, overwrite: bool = False):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        calculated_routes = routes_planner.get_routes(routes.depot_address,
                                                      routes.semi_depot_addresses,
                                                      routes.addresses,
                                                      routes.priorities,
                                                      routes.days,
                                                      routes.distance_limit,
                                                      routes.duration_limit,
                                                      routes.preferences,
                                                      routes.avoid_tolls)

        routes = routes_repo.create_user_route(uid, calculated_routes, routes.days, routes.distance_limit, routes.duration_limit, routes.preferences, routes.avoid_tolls, routes_id, overwrite)

    except ValueError as e:
        error = str(e)
        return JSONResponse(status_code=400, content={"error": error})

    return routes


@app.delete("/routes")
@logger.catch
def del_user_route(request: Request, active: bool = False, routes_id: str = None):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        resp = routes_repo.delete_user_route(uid,
                                             active,
                                             routes_id)
        return resp
        
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})

@app.post("/routes/waypoint")
@logger.catch
def mark_visited_waypoint(request: Request, waypoint: WaypointModel, should_keep: bool = False):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        updated_waypoint = routes_repo.update_waypoint(uid,
                                                       waypoint.routes_id,
                                                       waypoint.route_number,
                                                       waypoint.location_number,
                                                       waypoint.visited,
                                                       should_keep)

        return updated_waypoint

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/routes/rename")
@logger.catch
def change_name_of_routes(request: Request, rename: RenameModel):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        status = routes_repo.change_routes_name(rename.routes_id,
                                                rename.name)
        return status
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/routes/regenerate")
@logger.catch
def regenerate_routes(request: Request, regenerate: RegenerateModel, full_regeneration: bool = False):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        locations = routes_repo.get_locations_to_regenerate(regenerate.routes_id, full_regeneration)
        return locations
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})

@app.post("/stats")
@logger.catch
def get_statistics(request: Request, statistics: StatisticModel):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        stats = routes_repo.collect_stats(uid,
                                          statistics.start_date,
                                          statistics.end_date,
                                          False)
        return stats
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})

@app.get("/addresses")
@logger.catch
def get_used_locations(request: Request):
    uid = request.state.uid
    if uid is None:
        raise NotAuthenticated('User ID not found in token')
    try:
        addresses = routes_repo.collect_stats(uid,
                                              "01.01.2023",
                                              datetime.now().strftime("%d.%m.%y"),
                                              True)
        return addresses

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"error": e.detail})

# Keep this below all endpoint definitions!
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
