from pydantic import BaseModel, constr, Field
from typing import Optional


class RouteModel(BaseModel):
    addresses: list = Field([], description="List with 2 addresses in string format, returns route from first to second location")


class RoutesModel(BaseModel):
    depot_address: str = Field(..., description="The address of the depot")
    addresses: list = Field([], description="A list of addresses")
    priorities: list = Field([], description="A list of priorities, can be 1,2 or 3 (higher, the more important")
    days: int = Field(..., description="The number of days, there will be that many routes")
    distance_limit: float = Field(..., description="Daily distance limit, in km")
    duration_limit: float = Field(..., description="Daily duration limit in min")
    preferences: constr(regex='^(distance|duration|fuel)$') = Field(..., description="Preferences")
    avoid_tolls: bool = Field(..., description="Whether to avoid tolls")

class VisitedPointsModel(BaseModel):
    route_id: str
    route_point: list = []
    visited: bool
    warnings: Optional[str]