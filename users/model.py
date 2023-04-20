from pydantic import BaseModel


class UserModel(BaseModel):
    email: str
    password: str
    # created_at: Optional[str] = datetime.now().isoformat()
