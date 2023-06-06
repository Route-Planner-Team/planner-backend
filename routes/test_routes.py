from urllib import response

import pytest
from fastapi.testclient import TestClient
from main import app, routes_planner, routes_repo


@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

@pytest.fixture
def user_data():
    return {"email": "testowy23@gmail.com", "password": "test123!"}

@pytest.fixture
def auth_header(user_data, client):
    # {'_id': '64660a23b7ab38f24cfd4223', 'email': 'test_janusz@gmail.com', 'uid': 'uub8aAbFW3QFOAi49ql98KfHQIA2'}
    url = '/auth/sign-in'  # URL edpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    headers = {"Authorization": f"Bearer {auth_token}" }
    return headers

# INTEGRATION TESTS
@pytest.mark.skip(reason="Integration test with db")
def test_get_routes_integrate(client: TestClient, auth_header):
    routes = {
        "depot_address": "Naramowicka 219, 61-611 Poznań",
        "addresses": ["Rubież 46, C3 11, 61-612 Poznań",
                    "Rubież 14a/37, 61-612 Poznań",
                    "Radłowa 16, 61-602 Poznań",
                    "Zagajnikowa 9, 60-995 Poznań",
                    "Krótka 24, 62-007 Biskupice",
                    "Aleja Jana Pawła II 30, 93-570 Łódź",
                    "Jagiellońska 59, 85-027 Bydgoszcz"],
        "priorities": [2,1,3,2,1,2,3],
        "days": 1,
        "distance_limit":1000,
        "duration_limit": 1000,
        "preferences": "duration",
        "avoid_tolls": False
    }
    url = '/routes'
    response = client.post(url, json=routes, headers=auth_header)

    assert response


@pytest.mark.skip(reason="Integration test with db")
def test_get_routes_integrate(client: TestClient, auth_header):
    url = '/routes'
    response = client.get(url=url, headers=auth_header)
    assert response
    assert len(response) > 1


def test_get_routes():
    routes = {
        "depot_address": "Naramowicka 219, 61-611 Poznań",
        "addresses": ["Rubież 46, C3 11, 61-612 Poznań",
                    "Rubież 14a/37, 61-612 Poznań",
                    "Radłowa 16, 61-602 Poznań",
                    "Zagajnikowa 9, 60-995 Poznań",
                    "Krótka 24, 62-007 Biskupice",
                    "Aleja Jana Pawła II 30, 93-570 Łódź",
                    "Jagiellońska 59, 85-027 Bydgoszcz"],
        "priorities": [2,1,3,2,1,2,3],
        "days": 1,
        "distance_limit":1000,
        "duration_limit": 1000,
        "preferences": "duration",
        "avoid_tolls": False
    }
    route = routes_planner.get_routes(routes['depot_address'],
                                           routes['addresses'],
                                           routes['priorities'],
                                           routes['days'],
                                           routes['distance_limit'],
                                           routes['duration_limit'],
                                           routes['preferences'],
                                           routes['avoid_tolls'])

    assert route

    with pytest.raises(ValueError):
        # test with bad distance limit, 100 km, unreal to drive from all this points
        route = routes_planner.get_routes(routes['depot_address'],
                                           routes['addresses'],
                                           routes['priorities'],
                                           routes['days'],
                                           100,
                                           routes['duration_limit'],
                                           routes['preferences'],
                                           routes['avoid_tolls'])
        # should raise ValueError: Can not compute routes for this parameters. Modify parameters.

    with pytest.raises(ValueError):
        # test with bad duration limit, 250 km, its not enough
        route = routes_planner.get_routes(routes['depot_address'],
                                           routes['addresses'],
                                           routes['priorities'],
                                           routes['days'],
                                           routes['distance_limit'],
                                           250,
                                           routes['preferences'],
                                           routes['avoid_tolls'])
        # should raise ValueError: Can not compute routes for this parameters. Modify parameters.
