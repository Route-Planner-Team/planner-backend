from pydantic import BaseModel


class UserModel(BaseModel):
    email: str
    password: str


class UserModelChangePassword(BaseModel):
    new_password: str
    confirm_new_password: str


class UserEmailModel(BaseModel):
    email: str
