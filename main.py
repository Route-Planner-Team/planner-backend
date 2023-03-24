import firebase_admin
from fastapi import FastAPI, Request
from users.user_repository import UserRepository, UserModel
from loguru import logger
from config import Config
from fastapi_exceptions.exceptions import NotAuthenticated
from fastapi.middleware.cors import CORSMiddleware
from users.jwt import JWTAuth
from firebase_admin import credentials, auth


cred = credentials.Certificate("route_planner_service_account_keys.json")
firebase = firebase_admin.initialize_app(cred)
cfg = Config()
repo = UserRepository(cfg)
app = FastAPI()

app.add_middleware(
   CORSMiddleware,
   allow_origins=['*'],
   allow_credentials=True,
   allow_methods=['*'],
   allow_headers=['*']
)

'''
In postman -> POST https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=AIzaSyDP8Cmf8asXmcNGpX7wa0PGIPpHMHhBTe4
body as json -> {"email":"test@wp.pl","password":"test123","returnSecureToken":true}
u will get "idToken"
 
copy "idToken" and put into any request in Headers (key: Authorization, Value: Bearer <idToken>
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
    #s['token'] = JWTAuth.generate_jwt_token(s)
    return s

@app.post("/auth/sign-in")
@logger.catch
def login_user(user: UserModel):
    """
    Sign-in handler
    """
    try:
        status = repo.get_user(user.dict())
        #status['token'] = JWTAuth.generate_jwt_token(status)
        return status
    except NotAuthenticated:
        return {"Message": "Auth failed!"}


@app.get("/protected")
@logger.catch
def protected_handler(request: Request):
    try:
        auth_header = request.headers['Authorization']
        decoded = JWTAuth.authenticate(auth_header)
        resp = {}
        resp.update({"Email": decoded['email']})
        return resp
    except KeyError:
        print("No auth header")
        return {"Error": "No find token in headers"}