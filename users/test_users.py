from urllib import response

import pytest
from fastapi.testclient import TestClient
from firebase_admin._auth_utils import EmailAlreadyExistsError
from main import app, user_repo
from requests.exceptions import HTTPError


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

def test_sign_in(user_data, client):
    url = '/auth/sign-in'  # URL endpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    assert auth_token
    assert len(auth_token) > 20

def test_change_password(client, auth_header):
    params = {
        "new_password": "test123!",
        "confirm_new_password": "test123!"
    }

    response = client.post("/auth/change-password", json=params, headers=auth_header).json()

    assert response['email'] == 'route_planner_test@interia.pl'

def test_change_email(client, auth_header):
    params = {
        "email": "route_planner_test2@interia.pl"
    }

    response = client.post("/auth/change-email", json=params, headers=auth_header).json()

    assert response['message'] == "Email changed successfully"

    params = {
        "email": "route_planner_test@interia.pl"
    }

    response = client.post("/auth/change-email", json=params, headers=auth_header).json()

    assert response['message'] == "Email changed successfully"

def test_forgot_password(client):
    params = {
        "email": "route_planner_test@interia.pl"
    }

    response = client.post("/auth/forgot-password", json=params).json()

    assert response['email'] == "route_planner_test@interia.pl"

