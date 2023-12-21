from urllib import response

import pytest
from fastapi.testclient import TestClient
from main import app, routes_planner, routes_repo


# Fixtury dla testow integracyjnych
@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

@pytest.fixture
def user_data():
    return {"email": "route_planner_test@interia.pl", "password": "test123!"}

@pytest.fixture
def auth_header(user_data, client):
    # {'_id': '64660a23b7ab38f24cfd4223', 'email': 'test_janusz@gmail.com', 'uid': 'uub8aAbFW3QFOAi49ql98KfHQIA2'}
    url = '/auth/sign-in'  # URL endpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    headers = {"Authorization": f"Bearer {auth_token}" }
    return headers


def test_del_user_routes(client, auth_header):
    response = client.delete("/routes", headers=auth_header)

    assert response.json()['deleted_routes'] != -1


# Checks if 'tools' works
def check_tools():
    params1 = {
        "depot_address": "Nad Bogdanką 6a, 60-862 Poznań, Poland",
        "semi_depot_addresses": [],
        "addresses": ["Kwiatowa 43C, 66-400 Gorzów Wielkopolski, Poland"],
        "priorities": [3],
        "days": 1,
        "distance_limit":  None,
        "duration_limit": None,
        "preferences": "distance",
        "avoid_tolls": True
    }
    params2 = {
        "depot_address": "Nad Bogdanką 6a, 60-862 Poznań, Poland",
        "semi_depot_addresses": [],
        "addresses": ["Kwiatowa 43C, 66-400 Gorzów Wielkopolski, Poland"],
        "priorities": [3],
        "days": 1,
        "distance_limit": None,
        "duration_limit": None,
        "preferences": "distance",
        "avoid_tolls": False
    }
    routes1 = routes_planner.get_routes(params1['depot_address'],
                                        params1['semi_depot_addresses'],
                                        params1['addresses'],
                                        params1['priorities'],
                                        params1['days'],
                                        params1['distance_limit'],
                                        params1['duration_limit'],
                                        params1['preferences'],
                                        params1['avoid_tolls'])

    routes2 = routes_planner.get_routes(params2['depot_address'],
                                        params2['semi_depot_addresses'],
                                        params2['addresses'],
                                        params2['priorities'],
                                        params2['days'],
                                        params2['distance_limit'],
                                        params2['duration_limit'],
                                        params2['preferences'],
                                        params2['avoid_tolls'])

    assert routes1['routes']['subRoutes']['distance_km'] < routes2['routes']['subRoutes']['distance_km']


# Check if routes are saved into mongo
def test_save_routes(client, auth_header):
    routes = {
        "depot_address": "Nad Bogdanką 6a, 60-862 Poznań, Poland",
        "semi_depot_addresses": [],
        "addresses": ["Kassyusza 7, 60-549 Poznań, Poland",
            "Słowackiego 15, 60-822 Poznań, Poland"],
        "priorities": [3,2],
        "days": 2,
        "distance_limit":  None,
        "duration_limit": None,
        "preferences": "duration",
        "avoid_tolls": True
    }

    response = client.post("/routes", json=routes, headers=auth_header)

    routes = response.json()

    assert response.status_code == 200
    assert isinstance(routes, dict)


# Checks if endpoint returns all routes for user
def test_get_user_routes(client, auth_header):
    response = client.get("/routes", headers=auth_header)

    routes = response.json()

    assert isinstance(routes, dict)
    assert len(routes['routes']) >= 1


# Checks endpoint that updates waypoints
def test_update_waypoints(client, auth_header):
    routes = {
        "depot_address": "Nad Bogdanką 6a, 60-862 Poznań, Poland",
        "semi_depot_addresses": [],
        "addresses": ["Kassyusza 7, 60-549 Poznań, Poland",
            "Słowackiego 15, 60-822 Poznań, Poland"],
        "priorities": [3,2],
        "days": 2,
        "distance_limit":  None,
        "duration_limit": None,
        "preferences": "duration",
        "avoid_tolls": True
    }

    response = client.post("/routes", json=routes, headers=auth_header)
    response_data = response.json()
    routes_id = response_data['routes']['routes_id']

    # update every waypoint in first route
    for i in range(3):
        waypoint = {
            "routes_id": routes_id,
            "route_number": 0,
            "location_number": i,
            "visited": True
        }
        response = client.post("routes/waypoint", json=waypoint, headers=auth_header)

    assert response.json()['completed'] is True


# Check if endpoint routes/active returns only active routes
def test_get_user_active_routes(client, auth_header):
    all_response = client.get("/routes", headers=auth_header)
    active_response = client.get("/routes/active", headers=auth_header)

    all_routes = all_response.json()
    active_routes = active_response.json()

    assert len(all_routes['routes'][0]['subRoutes']) > len(active_routes['routes'][1]['subRoutes'])

def test_rename_routes(client, auth_header):
    all_response = client.get("/routes", headers=auth_header)
    routes_id = all_response.json()['routes'][0]['routes_id']

    params = {
        "routes_id": routes_id,
        "name": "test"
    }

    response = client.post("/routes/rename", json=params, headers=auth_header)

    all_response = client.get("/routes", headers=auth_header)

    assert all_response.json()['routes'][0]['name'] == "test"


def test_regenerate_routes(client, auth_header):
    all_response = client.get("/routes", headers=auth_header)
    routes_id = all_response.json()['routes'][1]['routes_id']

    params = {
        "routes_id": routes_id
    }

    response = client.post("/routes/regenerate", json=params, headers=auth_header)

    assert len(response.json()['addresses']) == 1


def test_stats(client, auth_header):
    params = {
        "start_date": "01.01.2023",
        "end_date": "31.12.2023"
    }

    response = client.post("/stats", json=params, headers=auth_header)

    assert response.json()['number_of_completed_routes'] != 0


def test_get_addresses(client, auth_header):
    addresses = client.get("/addresses", headers=auth_header)

    assert addresses.json()['addresses'] != 0


# Check if endpoints deletes all routes for user
def test_del_user_routes(client, auth_header):
    response = client.delete("/routes", headers=auth_header)

    assert response.json()['deleted_routes'] >= 1
