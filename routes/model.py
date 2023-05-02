from pydantic import BaseModel


class RouteModel(BaseModel):
    address: list = []

class RoutesModel(BaseModel):
    depot_address: str
    address: list = []
    days: int
    distance_limit: int
    duration_limit: int
    avg_fuel_consumption: int