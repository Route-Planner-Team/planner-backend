import requests
import polyline
import logging
from loguru import logger
from config import Config

class RoutePlanner():
    def __init__(self, config):
        self.config = config

    def calculate_route(self, addresses):
        pass

        # addresses = [
        #     "1600 Amphitheatre Parkway, Mountain View, CA",
        #     "345 Park Ave, San Jose, CA",
        #     "1 Hacker Way, Menlo Park, CA",
        #     "350 Rhode Island St, San Francisco, CA"
        # ]

        response = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": addresses[0],
                "destination": addresses[-1],
                "key": self.config.GOOGLEMAPS_API_KEY
            }
        )

        if response.status_code != 200:
            return {"error": "Failed to calculate route"}

        data = response.json()
        # print(data)

        points = []

        steps = data['routes'][0]['legs'][0]['steps']

        tmp_array = []
        for step in steps:
            polyline_str = step['polyline']['points']
            tmp_array.append(polyline_str)

            decoded_polyline = polyline.decode(polyline_str)


            points.extend(decoded_polyline)

        return {"route": points}
