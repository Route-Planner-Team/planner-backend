from urllib import response
import pytest
from fastapi.testclient import TestClient
from main import app
from main import user_repo
from firebase_admin._auth_utils import EmailAlreadyExistsError
from requests.exceptions import HTTPError

@pytest.fixture
def client():
    return TestClient(app)  # client to test (like app, fast api object, FastApi() )

@pytest.fixture
def user_data():
    return {"email": "testowy23@gmail.com", "password": "test123!"}

def test_sign_in(user_data, client):
    # {'_id': '64660a23b7ab38f24cfd4223', 'email': 'test_janusz@gmail.com', 'uid': 'uub8aAbFW3QFOAi49ql98KfHQIA2'}
    url = '/auth/sign-in'  # URL edpoint to some handler
    response = client.post(url, json=user_data).json()
    auth_token = response['access_token']

    assert auth_token
    assert len(auth_token) > 20

    url = '/protected'
    headers = {"Authorization": f"Bearer {auth_token}" }
    response = client.get(url, headers=headers).json()

    assert response['user_firebase_id']
    assert len(response['user_firebase_id']) > 10
