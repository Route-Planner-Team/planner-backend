from pydantic import BaseModel, constr


class RouteModel(BaseModel):
    address: list = []

class RoutesModel(BaseModel):
    depot_address: str
    address: list = []
    days: int
    distance_limit: int
    duration_limit: int
    preferences: constr(regex='^(distance|duration)$')