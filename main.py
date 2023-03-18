from fastapi import FastAPI, Request
from users.user_repository import UserRepository, UserModel
from loguru import logger
from config import Config
from fastapi_exceptions.exceptions import NotAuthenticated
from users.jwt import JWTAuth

cfg = Config()
repo = UserRepository(cfg)
app = FastAPI()


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
    s['token'] = JWTAuth.generate_jwt_token(s)
    return s


@app.post("/auth/sign-in")
@logger.catch
def login_user(user: UserModel):
    """
    Sign-in handler
    """
    try:
        status = repo.get_user(user.email, user.password)
        status['token'] = JWTAuth.generate_jwt_token(status)
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