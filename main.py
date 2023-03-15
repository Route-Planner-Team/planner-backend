from fastapi import FastAPI, Header, Request
from repository.user_repository import UserRepository, UserModel
from config import Config
from loguru import logger


cfg = Config()
repo = UserRepository(cfg)
app = FastAPI()


@app.get("/")
def ping():
    return {"message": "pong"}


@app.post("/auth/registration")
@logger.catch
def create_user(user: UserModel):
    """
    Handler to create user
    :param user:
    :return: {"email": ...., "created_at": ...}
    """
    logger.info(user)
    s = repo.create_user(user.dict())
    return {"message": s}


@app.post("/auth/login")
@logger.catch
def login_user(user: UserModel, request: Request):
    # TODO
    # try to read token from headers
    # print(request.headers)
    # if KeyError or don't found or cannot parse read email and password, if token is ok - return updated token

    # if token in headers is empty , warning, can throw KeyError exception
    logger.info(user)
    # now return only true or false
    status = repo.get_user(user.email, user.password)
    return {"Status": status}
