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
    return {"email": "testowy23@gmail.com", "password": "test123!"}

def test_sign_in(user_data, client):
    url = '/auth/sign-in'  # URL endpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']
    assert auth_token
    assert len(auth_token) > 20

