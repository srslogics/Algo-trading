import pytest
from fastapi.testclient import TestClient

from optionlab.api.app import create_app
from optionlab.config import Settings
from optionlab.db import Database
from optionlab.models import Base


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, database_url=f"sqlite:///{tmp_path}/test.db")


@pytest.fixture
def database(settings):
    db = Database(settings)
    Base.metadata.create_all(db.engine)
    return db


@pytest.fixture
def client(settings, database):
    with TestClient(create_app(settings, database)) as client:
        yield client


@pytest.fixture
def proposal(client):
    assert client.post("/api/v1/demo/tick", json={}).status_code == 200
    response = client.post("/api/v1/proposals", json={})
    assert response.status_code == 200
    return response.json()
