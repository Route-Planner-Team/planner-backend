from pydantic import BaseModel, constr, Field
from typing import Optional


class RouteModel(BaseModel):
    addresses: list = []


class RoutesModel(BaseModel):
    depot_address: str
    addresses: list = []
    priorities: list = []
    days: int
    distance_limit: int
    duration_limit: int
    preferences: constr(regex='^(distance|duration|fuel)$')
    avoid_tolls: bool
    #user_email: Optional[str] = Field(required=False)

class MarkPointModel(BaseModel):
    route_id: str
    id_of_route_for_special_day: str
    info_about_points: list = []  # list of list
    is_this_route_ended: bool = False