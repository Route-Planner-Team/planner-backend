from pydantic import BaseModel


class UserModel(BaseModel):
    email: str
    password: str
    # created_at: Optional[str] = datetime.now().isoformat()


class UserModelChangePassword(BaseModel):
    email: str
    new_password: str
    confirm_new_password: str


class UserModelForgotPassword(BaseModel):
    email: str