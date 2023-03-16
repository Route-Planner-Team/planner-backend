from fastapi import FastAPI, Header, Request
from repository.user_repository import UserRepository, UserModel
from loguru import logger
import os
from dotenv import load_dotenv


class Config():
    load_dotenv()
    mongo_conn: str = os.getenv("MONGO", "")


cfg = Config()
repo = UserRepository(cfg)
app = FastAPI()


@app.get("/")
def ping():
    return {"message": "pong"}


@app.post("/auth/sign-up")
@logger.catch
def create_user(user: UserModel):
    """
    Handler to create user
    :param user:
    :return: {"email": ...., "created_at": ...}
    """

    s = repo.create_user(user.dict())
    return {"message": s}


@app.post("/auth/sign-in")
@logger.catch
def login_user(user: UserModel, request: Request):
    # TODO
    # try to read token from headers
    # Can check headers in request.headers
    try:
        auth_header = request.headers['Auth']
        print(f"Auth header {auth_header}")
    except KeyError:
        print("No auth header")
        pass
    # if KeyError or don't found or cannot parse read email and password, if token is ok - return updated token

    # if token in headers is empty , warning, can throw KeyError exception
    # now return only true or false
    status = repo.get_user(user.email, user.password)
    return {"Status": status}
