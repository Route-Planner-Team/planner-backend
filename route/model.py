from pydantic import BaseModel


class RouteModel(BaseModel):
    address: list = []
