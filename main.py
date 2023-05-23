import firebase_admin
from fastapi import FastAPI, Request
from users.user_repository import UserRepository
from users.model import UserModel, UserModelChangePassword, UserEmailModel
from loguru import logger
from config import Config
from fastapi_exceptions.exceptions import NotAuthenticated
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth
import googlemaps
from routes.model import RouteModel, RoutesModel
from routes.planner import RoutesPlanner
from routes.route_repository import RouteRepository
from users.auth import authenticate_header

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

        change_key_name(firebase_payload, "idToken", "acces_token")
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
    return status


@app.post("/auth/forgot-password")
@logger.catch
def forgot_password(user: UserEmailModel):
    """
    Handler to change password for not logged in user
    """

    status = user_repo.forgot_password(user.dict())
    return status


@app.get("/protected")
@logger.catch
def protected_handler(request: Request):
    return {"user_id" :request.state.uid}

@app.post("/route")
@logger.catch
def route_handler(route: RouteModel):
    route = routes_planner.calculate_route(route.address) # type: ignore
    return route


# endpoint is protected, so do instructions from line 51
@app.post("/routes")
@logger.catch
def routes_handler(request: Request, routes: RoutesModel):
    uid = request.state.uid
    if uid is None :
        raise NotAuthenticated('User ID not found in token')

    routes = routes_planner.get_routes(routes.depot_address,
                                       routes.address,
                                       routes.days,
                                       routes.distance_limit,
                                       routes.duration_limit,
                                       routes.preferences,
                                       routes.avoid_tolls) # type: ignore

    # add logic to add users_route to db
    routes = routes_repo.create_user_route(uid, routes) # type: ignore
    return routes

@app.get("/user_route")
@logger.catch
def get_user_route(request: Request):
    uid = request.state.uid
    s = routes_repo.get_user_route(uid=uid)
    return {"Result": s}

@app.delete("/user_route")
@logger.catch
def del_user_route(request: Request):
    uid = request.state.uid
    print(uid)
    count = routes_repo.delete_user_route(uid=uid)
    return {"Deleted": count}
