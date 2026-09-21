"""Opt-in integration test against an empty, disposable PostgreSQL database."""

import os
import secrets
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from optionlab.api.app import create_app
from optionlab.config import Settings


@pytest.mark.skipif(
    not os.getenv("OPTIONLAB_TEST_POSTGRES_URL"), reason="Disposable PostgreSQL URL not supplied"
)
def test_postgres_migration_concurrent_fills_and_restart(monkeypatch):
    url = os.environ["OPTIONLAB_TEST_POSTGRES_URL"]
    monkeypatch.setenv("OPTIONLAB_DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    token = secrets.token_urlsafe(32)
    settings = Settings(
        _env_file=None,
        database_url=url,
        environment="render",
        auth_required=True,
        api_token=token,
        public_origin="https://optionlab-test.onrender.com",
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(create_app(settings), base_url=settings.public_origin, headers=headers) as c:
        assert c.get("/api/v1/paper/orders").json() == [], "Use an empty disposable test database"
        assert c.post("/api/v1/demo/tick", json={}).status_code == 200
        proposal = c.post("/api/v1/proposals", json={}).json()
        payload = {"proposal_id": proposal["id"], "idempotency_key": "ci-concurrent-entry"}
        with ThreadPoolExecutor(max_workers=6) as executor:
            results = list(
                executor.map(lambda _: c.post("/api/v1/paper/orders", json=payload), range(6))
            )
        assert all(r.status_code == 200 for r in results)
        ids = {r.json()["order"]["id"] for r in results}
        assert len(ids) == 1
        balance = c.get("/api/v1/overview").json()["cash"]
        position_id = results[0].json()["order"]["position_id"]
    with TestClient(create_app(settings), base_url=settings.public_origin, headers=headers) as c:
        assert c.get("/api/v1/overview").json()["cash"] == balance
        assert len(c.get("/api/v1/paper/orders").json()) == 1
        assert c.post("/api/v1/paper/orders", json=payload).json()["replayed"] is True
        assert c.post("/api/v1/demo/tick", json={}).status_code == 200
        assert (
            c.post(
                f"/api/v1/positions/{position_id}/close", json={"idempotency_key": "ci-manual-exit"}
            ).status_code
            == 200
        )
        assert c.get("/api/v1/overview").json()["open_positions"] == 0
    command.check(Config("alembic.ini"))
