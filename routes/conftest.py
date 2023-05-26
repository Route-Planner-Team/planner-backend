import pytest
from main import routes_repo
from firebase_admin import auth

def pytest_sessionfinish(session, exitstatus):
    # This code will be executed as teardown after all tests
    # Put your teardown code here
    print("Teardown after all tests")
    # firebase_user = auth.get_user(uid)
    routes_repo.delete_user_route(uid="uub8aAbFW3QFOAi49ql98KfHQIA2")
