import copy

import pytest

import data
from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


@pytest.fixture(autouse=True)
def reset_inventory():
    """Restore the mock database after every test so tests don't affect each other."""
    original = copy.deepcopy(data.inventory)
    yield
    data.inventory[:] = original