import pytest
from fastapi.testclient import TestClient
from main import app  # maybe should be into tests package, but we should move main.py to app directory

@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

def test_route_endpoint(client):
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