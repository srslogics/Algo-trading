from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from optionlab import server
from optionlab.api.app import create_app
from optionlab.config import Settings
from optionlab.db import Database
from optionlab.models import Account


def test_server_migrates_empty_database_and_preserves_account_on_restart(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path}/deployment.db"
    monkeypatch.setenv("OPTIONLAB_DATABASE_URL", url)
    monkeypatch.setenv("PORT", "10000")
    settings = Settings(_env_file=None, database_url=url)
    starts = []

    def start_app(*args, **kwargs):
        assert kwargs["port"] == 10000
        assert kwargs["workers"] == 1
        assert kwargs["host"] == "0.0.0.0"
        db = Database(settings)
        assert "accounts" in inspect(db.engine).get_table_names()
        with TestClient(create_app(settings, db)) as client:
            starts.append(client.get("/api/v1/overview").json()["cash"])
            assert client.get("/healthz").status_code == 200
            with db.transaction(write=True) as session:
                session.get(Account, "paper").cash = Decimal("432100")

    monkeypatch.setattr(server.uvicorn, "run", start_app)
    server.main()
    server.main()
    assert Decimal(starts[0]) == settings.starting_cash
    assert Decimal(starts[1]) == Decimal("432100")


def test_failed_migration_never_starts_web_server(monkeypatch):
    runner = Mock()
    monkeypatch.setattr(server.uvicorn, "run", runner)
    monkeypatch.setattr(
        server.command, "upgrade", Mock(side_effect=RuntimeError("migration failed"))
    )
    with pytest.raises(RuntimeError, match="migration failed"):
        server.main()
    runner.assert_not_called()
