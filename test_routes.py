from urllib import response
import pytest
from fastapi.testclient import TestClient
from main import app  # maybe should be into tests package, but we should move main.py to app directory

@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

def test_route_endpoint(client: TestClient):
    url = '/route'  # URL edpoint to some handler
    data = {
        "address": [
            "1600 Amphitheatre Parkway, Mountain View, CA",
            "345 Park Ave, San Jose, CA",
            "1 Hacker Way, Menlo Park, CA",
            "350 Rhode Island St, San Francisco, CA"
        ]
    }

    response = client.post(url, json=data)
    route = response.json().get('route', [])

    assert len(route) > 1, "Expected length of route to be greater than 1"


#

def test_planner_endpoint(client: TestClient):
    url = '/routes'
    data = {
        "depot_address": "Naramowicka 219, 61-611 Poznań",
        "address": ["Rubież 46, C3 11, 61-612 Poznań",
                    "Rubież 14a/37, 61-612 Poznań",
                    "Radłowa 16, 61-602 Poznań",
                    "Zagajnikowa 9, 60-995 Poznań"],
        "days": 1,
        "distance_limit":30,
        "duration_limit": 10000,
        "avg_fuel_consumption": 6
    }

    response = client.post(url, json=data)
    route = response.json()
    

    assert response.status_code == 200
    assert response.content != "null"
