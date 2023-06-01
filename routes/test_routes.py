from urllib import response
import pytest
from fastapi.testclient import TestClient
from main import app
from main import routes_repo

@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

@pytest.fixture
def user_data():
    return {"email": "test_janusz@gmail.com", "password": "asbchvajbhsc"}

@pytest.fixture
def auth_header(user_data, client):
    # {'_id': '64660a23b7ab38f24cfd4223', 'email': 'test_janusz@gmail.com', 'uid': 'uub8aAbFW3QFOAi49ql98KfHQIA2'}
    url = '/auth/sign-in'  # URL edpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    headers = {"Authorization": f"Bearer {auth_token}" }
    return headers


def test_route_endpoint(client: TestClient):
    url = '/route'  # URL endpoint to some handler
    data = {
        "addresses": [
            "1600 Amphitheatre Parkway, Mountain View, CA",
            "345 Park Ave, San Jose, CA",
            "1 Hacker Way, Menlo Park, CA",
            "350 Rhode Island St, San Francisco, CA"
        ]
    }

    response = client.post(url, json=data)
    route = response.json().get('coords', [])

    assert len(route) > 1, "Expected length of route to be greater than 1"

def test_planner_endpoint_one_day(client: TestClient, auth_header):
    url = '/routes'
    data = {
        "depot_address": "Naramowicka 219, 61-611 Poznań",
        "addresses": ["Rubież 46, C3 11, 61-612 Poznań",
                    "Rubież 14a/37, 61-612 Poznań",
                    "Radłowa 16, 61-602 Poznań",
                    "Zagajnikowa 9, 60-995 Poznań",
                    "Krótka 24, 62-007 Biskupice",
                    "Aleja Jana Pawła II 30, 93-570 Łódź",
                    "Jagiellońska 59, 85-027 Bydgoszcz"],
        "priorities": [2,1,3,2,1,2,3],
        "days": 2,
        "distance_limit":500,
        "duration_limit": 10000,
        "preferences": "duration",
        "avoid_tolls": False
    }

    response = client.post(url, json=data, headers=auth_header)
    route = response.json()


    assert response.status_code == 200
    assert response.content != "null"

def test_save_user_route(client: TestClient, auth_header):
    url = '/routes'
    data = {
        "depot_address": "Naramowicka 219, 61-611 Poznań",
        "addresses": ["Rubież 46, C3 11, 61-612 Poznań",
                    "Rubież 14a/37, 61-612 Poznań",
                    "Radłowa 16, 61-602 Poznań",
                    "Zagajnikowa 9, 60-995 Poznań"],
        "priorities": [3,2,1,2],
        "days": 1,
        "distance_limit":50,
        "duration_limit": 1000,
        "preferences": "duration",
        "avoid_tolls": False
    }

    response = client.post(url, json=data, headers=auth_header)
    # print(response.json())

    assert response.status_code == 200
    assert response.content != "null"

def test_find_user_route_by_email(client: TestClient, auth_header):
    url = '/user_route'
    response = client.get(url, headers=auth_header)
    print(response.json())
    assert response.status_code == 200


def test_update_user_route_via_day_id():
    body = {
        "route_id": "123",
        "id_of_route_for_special_day": "1",
        "info_about_points": [[1, 2,True,'abc'], [3,4, False, "qwe"]],
        "is_this_route_ended": False
    }
    res = routes_repo.update_document_via_day_id(body=body)
    assert res != -1