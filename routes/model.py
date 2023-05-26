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

class VisitedPointsModel(BaseModel):
    route_id: str
    route_point: list = []
    visited: bool
    warnings: Optional[str]