import firebase_admin
from fastapi import FastAPI, Request
from users.user_repository import UserRepository
from users.model import UserModel
from loguru import logger
from config import Config
from fastapi_exceptions.exceptions import NotAuthenticated
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, auth
import googlemaps
from routes.model import RouteModel
from routes.model import RoutesModel
from routes.planner import RoutesPlanner
from routes.route_repository import RouteRepository


cfg = Config()

repo = UserRepository(cfg)
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


@app.middleware("http")
async def firebase_middleware(request: Request, call_next):
    return await UserRepository.authenticate_header(request, call_next)


@app.get("/")
def ping():
    return {"message": "pong"}


@app.post("/auth/sign-up")
@logger.catch
def create_user(user: UserModel, status_code=201):
    """
    Handler to create user
    """

    s = repo.create_user(user.dict())
    return s


@app.post("/auth/sign-in")
@logger.catch
def login_user(user: UserModel):
    """
    Sign-in handler
    """
    try:
        status = repo.get_user(user.dict())
        return status
    except NotAuthenticated:
        return {"Message": "Auth failed!"}


@app.get("/protected")
@logger.catch
def protected_handler():
    return {"message": "Authorization gained"}


@app.get("/test")
@logger.catch
def protected_handler():
    return {"message": "Authorization gained"}


@app.post("/route")
@logger.catch
def route_handler(route: RouteModel):
    route = routes_planner.calculate_route(route.address)
    return route

@app.post("/routes")
@logger.catch
def routes_handler(routes: RoutesModel):
    user_email = routes.user_email
    routes = routes_planner.get_routes(routes.depot_address,
                                       routes.address,
                                       routes.days,
                                       routes.distance_limit,
                                       routes.duration_limit,
                                       routes.preferences)
    if user_email is not None:
        # add logic to add users_route to db
        r = routes_repo.create_user_route(user_email, routes)
        return r

    return routes

@app.get("/routes")
def get_user_route(email: str):
    s = routes_repo.get_route_by_user_email(email=email)
    return {"Result": s}
