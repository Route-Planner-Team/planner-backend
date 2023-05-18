import pytest
from main import routes_repo

def pytest_sessionfinish(session, exitstatus):
    # This code will be executed as teardown after all tests
    # Put your teardown code here
    print("Teardown after all tests")
    routes_repo.delete_user_route(email="test_user@gmail.com")
