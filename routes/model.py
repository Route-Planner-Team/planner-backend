from pydantic import BaseModel, constr, Field

class RoutesModel(BaseModel):
    depot_address: str = Field(..., description="The address of the depot")
    addresses: list = Field([], description="A list of addresses")
    priorities: list = Field([], description="A list of priorities, can be 1,2 or 3 (higher, the more important")
    days: int = Field(..., description="The number of days, there will be that many routes")
    distance_limit: float = Field(..., description="Daily distance limit, in km")
    duration_limit: float = Field(..., description="Daily duration limit in min")
    preferences: constr(regex='^(distance|duration|fuel)$') = Field(..., description="Preferences")
    avoid_tolls: bool = Field(..., description="Whether to avoid tolls")

class WaypointModel(BaseModel):
    routes_id: str = Field(..., description="Database id of a set of routes, generated together")
    route_number: int = Field(..., description="Id of a single route in a set")
    location_number: int = Field(..., description="Number for a  waypoint in a route")
    visited: bool = Field(..., description="True if visited, False by default")
    comment: str = Field(..., description="Comment for a waypoint")
