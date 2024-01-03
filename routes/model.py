from pydantic import BaseModel, constr, Field
from typing import Optional, List

class RoutesModel(BaseModel):
    depot_address: str = Field(..., description="The address of the depot")
    semi_depot_addresses: Optional[List[str]] = Field([], description="A list of semi depot addresses")
    addresses: list = Field([], description="A list of addresses")
    priorities: list = Field([], description="A list of priorities, can be 1,2 or 3 (higher, the more important")
    days: int = Field(..., description="The number of days, there will be that many routes")
    distance_limit: Optional[float] = Field(None, description="Daily distance limit, in km")
    duration_limit: Optional[float] = Field(None, description="Daily duration limit in min")
    preferences: constr(regex='^(distance|duration|fuel)$') = Field(..., description="Preferences")
    avoid_tolls: bool = Field(..., description="Whether to avoid tolls")

class WaypointModel(BaseModel):
    routes_id: str = Field(..., description="Database id of a set of routes, generated together")
    route_number: int = Field(..., description="Id of a single route in a set")
    location_number: int = Field(..., description="Number for a  waypoint in a route")
    visited: bool = Field(..., description="True if visited, False by default")

class RegenerateModel(BaseModel):
    routes_id: str = Field(..., description="Collection of routes for which we want to regenerate + unvisited locations from that collection")

class StatisticModel(BaseModel):
    start_date: str = Field(..., description="From when we want to get stats, format DD.MM.YYYY")
    end_date: str = Field(..., description="To when we want to get stats, format DD.MM.YYYY")

class RenameModel(BaseModel):
    routes_id: str = Field(..., description="Collection of routes for which we want to change name")
    name: str = Field(..., description="New name for routes")

class WaypointInfoModel(BaseModel):
    routes_id: str = Field(..., description="Database id of a set of routes, generated together")
    route_number: int = Field(..., description="Id of a single route in a set")