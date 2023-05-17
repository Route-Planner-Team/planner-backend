from pydantic import BaseModel, constr, Field
from typing import Optional


class RouteModel(BaseModel):
    address: list = []

class RoutesModel(BaseModel):
    depot_address: str
    address: list = []
    days: int
    distance_limit: int
    duration_limit: int
    preferences: constr(regex='^(distance|duration)$')
    avoid_tolls: bool
    user_email: Optional[str] = Field(required=False)