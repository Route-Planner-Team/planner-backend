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
    return {"email": "testowy23@gmail.com", "password": "test123!"}

@pytest.fixture
def auth_header(user_data, client):
    # {'_id': '64660a23b7ab38f24cfd4223', 'email': 'test_janusz@gmail.com', 'uid': 'uub8aAbFW3QFOAi49ql98KfHQIA2'}
    url = '/auth/sign-in'  # URL endpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    headers = {"Authorization": f"Bearer {auth_token}" }
    return headers

# Checks if 'preferences' works
def check_duration_diff():
    # when preference is duration
    params1 = {
        "depot_address": "Święty Marcin 80/82, 61-809 Poznań",
        "addresses": ["Kraszewskiego 9B, 60-501 Poznań",
                    "Szpitalna 27/33, 60-572 Poznań",
                    "Warmińska 2, 60-622 Poznań",
                    "Aleje Solidarności 42, 61-696 Poznań",
                    "Szarych Szeregów 16, 60-462 Poznań",
                    "Dworksa 1, 61-619 Poznań",
                    "Kępa 1, 60-021 Poznań",
                    "Gdańska 2, 61-123 Poznań",
                    "Szwajcarska 14, 61-285 Poznań",
                    "świętego Antoniego 61, 61-359 Poznań",
                    "62-030, Powstańców Wielkopolskich, 61-030 Luboń"],
        "priorities": [2,1,3,2,1,2,3,2,1,3,2],
        "days": 3,
        "distance_limit":1000000,
        "duration_limit": 1000000,
        "preferences": "duration",
        "avoid_tolls": False
    }
    # when preference is distance
    params2 = {
        "depot_address": "Święty Marcin 80/82, 61-809 Poznań",
        "addresses": ["Kraszewskiego 9B, 60-501 Poznań",
                    "Szpitalna 27/33, 60-572 Poznań",
                    "Warmińska 2, 60-622 Poznań",
                    "Aleje Solidarności 42, 61-696 Poznań",
                    "Szarych Szeregów 16, 60-462 Poznań",
                    "Dworksa 1, 61-619 Poznań",
                    "Kępa 1, 60-021 Poznań",
                    "Gdańska 2, 61-123 Poznań",
                    "Szwajcarska 14, 61-285 Poznań",
                    "świętego Antoniego 61, 61-359 Poznań",
                    "62-030, Powstańców Wielkopolskich, 61-030 Luboń"],
        "priorities": [2,1,3,2,1,2,3,2,1,3,2],
        "days": 3,
        "distance_limit":1000000,
        "duration_limit": 1000000,
        "preferences": "distance",
        "avoid_tolls": False
    }
    routes1 = routes_planner.get_routes(params1['depot_address'],
                                        params1['addresses'],
                                        params1['priorities'],
                                        params1['days'],
                                        params1['distance_limit'],
                                        params1['duration_limit'],
                                        params1['preferences'],
                                        params1['avoid_tolls'])

    routes2 = routes_planner.get_routes(params2['depot_address'],
                                        params2['addresses'],
                                        params2['priorities'],
                                        params2['days'],
                                        params2['distance_limit'],
                                        params2['duration_limit'],
                                        params2['preferences'],
                                        params2['avoid_tolls'])

    total_duration_routes1 = sum(route['duration_hours'] for route in routes1.value())
    total_duration_routes2 = sum(route['duration_hours'] for route in routes2.value())

    assert total_duration_routes1 < total_duration_routes2


# Check if routes are saved into mongo
def test_save_routes(client, auth_header):
    routes = {
        "depot_address":"Święty Marcin 80/82, 61-809 Poznań",
        "addresses":["Kraszewskiego 9B, 60-501 Poznań",
                    "Kwiatowa 43c, 66-400 Gorzów Wielkopolski",
                    "62-030, Powstańców Wielkopolskich 79, 61-030 Luboń"],
        "priorities": [1,1,2],
        "days": 1,
        "distance_limit": 100000,
        "duration_limit": 100000,
        "preferences": "distance",
        "avoid_tolls": True
    }

    response = client.post("/routes", json=routes, headers=auth_header)

    routes = response.json()

    assert response.status_code == 200
    assert isinstance(routes, dict)
    assert len(routes) == 6


# Checks if endpoint returns all routes for user
def test_get_user_routes(client, auth_header):
    response = client.get("/routes", headers=auth_header)

    routes = response.json()

    assert isinstance(routes, dict)
    assert len(routes) >= 1


# Checks endpoint that updates waypoints
def test_update_waypoints(client, auth_header):
    routes = {
        "depot_address": "Święty Marcin 80/82, 61-809 Poznań",
        "addresses": ["Kraszewskiego 9B, 60-501 Poznań",
                      "Kwiatowa 43c, 66-400 Gorzów Wielkopolski",
                      "62-030, Powstańców Wielkopolskich 79, 61-030 Luboń"],
        "priorities": [1, 1, 2],
        "days": 1,
        "distance_limit": 100000,
        "duration_limit": 100000,
        "preferences": "distance",
        "avoid_tolls": True
    }

    response = client.post("/routes", json=routes, headers=auth_header)
    response_data = response.json()
    routes_id = response_data['routes_id']

    # update every waypoint in first route
    for i in range(5):
        waypoint = {
            "routes_id": routes_id,
            "route_number": 0,
            "location_number": i,
            "visited": True,
            "comment": "Visited waypoint"
        }
        response = client.post("routes/waypoint", json=waypoint, headers=auth_header)

    assert response.json()['0']['completed'] is True
    assert response.json()['routes_completed'] is True


# Check if endpoint routes/active returns only active routes
def test_get_user_active_routes(client, auth_header):
    all_response = client.get("/routes", headers=auth_header)
    active_response = client.get("/routes/active", headers=auth_header)

    all_routes = all_response.json()
    active_routes = active_response.json()

    assert len(all_routes) > len(active_routes)


# Check if endpoints deletes all routes for user
def test_del_user_routes(client, auth_header):
    response = client.delete("/routes", headers=auth_header)

    assert response.json()['deleted'] >= 1
