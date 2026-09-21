import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from optionlab.api.app import create_app
from optionlab.api.auth import COOKIE, issue_session, valid_session
from optionlab.config import Settings

ORIGIN = "https://optionlab-test.onrender.com"
TEST_KEY = "test-only-key-not-for-deployment-12345678"


def hosted(settings):
    return settings.model_copy(
        update={"auth_required": True, "api_token": SecretStr(TEST_KEY), "public_origin": ORIGIN}
    )


def test_render_environment_aliases(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@private:5432/optionlab")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", ORIGIN)
    s = Settings(_env_file=None, environment="render", auth_required=True, api_token=TEST_KEY)
    assert s.database_url == "postgresql+psycopg://user:pass@private:5432/optionlab"
    assert s.public_origin == ORIGIN
    monkeypatch.setenv("OPTIONLAB_DATABASE_URL", "postgresql://u:p@other/db")
    assert Settings(_env_file=None).database_url == "postgresql+psycopg://u:p@other/db"


def test_render_rejects_ephemeral_database_and_insecure_settings():
    with pytest.raises(ValidationError, match="authentication"):
        Settings(_env_file=None, environment="render", database_url="postgres://u:p@db/x")
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(_env_file=None, environment="render", auth_required=True, api_token=TEST_KEY)
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(
            _env_file=None,
            environment="render",
            auth_required=True,
            api_token=TEST_KEY,
            database_url="postgres://u:p@db/x",
            public_origin="http://app.example",
        )
    for origin in [
        "https://app.example/path",
        "https://user:pass@app.example",
        "https://app.example?x=1",
    ]:
        with pytest.raises(ValidationError):
            Settings(_env_file=None, public_origin=origin)


def test_secure_browser_session_and_csrf(settings, database):
    with TestClient(create_app(hosted(settings), database), base_url=ORIGIN) as c:
        assert c.get("/auth/session").json()["authenticated"] is False
        assert c.post("/auth/login", json={"token": "wrong"}).status_code == 401
        assert c.post("/auth/login", json={"token": "🔑"}).status_code == 401
        response = c.post("/auth/login", json={"token": TEST_KEY}, headers={"Origin": ORIGIN})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie
        assert TEST_KEY not in cookie
        assert c.get("/auth/session").json()["authenticated"] is True
        assert c.get("/api/v1/overview").status_code == 200
        assert c.post("/api/v1/demo/tick", json={}).status_code == 403
        assert (
            c.post(
                "/api/v1/demo/tick", json={}, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert c.post("/api/v1/demo/tick", json={}, headers={"Origin": ORIGIN}).status_code == 200
        assert c.post("/auth/logout", json={}, headers={"Origin": ORIGIN}).status_code == 200
        assert c.get("/api/v1/overview").status_code == 401


def test_proxy_https_origin_does_not_depend_on_forwarded_headers(settings, database):
    # Render terminates HTTPS while the app server receives HTTP internally.
    with TestClient(
        create_app(hosted(settings), database), base_url=ORIGIN.replace("https", "http")
    ) as c:
        login = c.post("/auth/login", json={"token": TEST_KEY}, headers={"Origin": ORIGIN})
        assert login.status_code == 200
        assert "Secure" in login.headers["set-cookie"]
        session = login.cookies.get(COOKIE)
        result = c.post(
            "/api/v1/demo/tick",
            json={},
            headers={"Origin": ORIGIN, "Cookie": f"{COOKIE}={session}"},
        )
        assert result.status_code == 200
        assert "max-age" in result.headers["strict-transport-security"]
        assert c.get("/", headers={"Host": "evil.example"}).status_code == 403
        assert c.get("/healthz", headers={"Host": "internal:10000"}).status_code == 200
        assert (
            c.get("/api/v1/overview", headers={"Authorization": "Bearer " + TEST_KEY}).status_code
            == 200
        )


def test_sessions_expire_and_cannot_be_tampered_or_reused_after_key_rotation():
    cookie = issue_session(TEST_KEY, 1)
    assert valid_session(cookie, TEST_KEY)
    assert not valid_session(cookie + "x", TEST_KEY)
    assert not valid_session(cookie, TEST_KEY + "rotated")
    assert not valid_session("v1.9999999999." + "x" * 32 + ".🔑", TEST_KEY)
    with patch("optionlab.api.auth.time.time", return_value=time.time() + 3601):
        assert not valid_session(cookie, TEST_KEY)


def test_login_is_rate_limited(settings, database):
    with TestClient(create_app(hosted(settings), database), base_url=ORIGIN) as c:
        for _ in range(20):
            assert c.post("/auth/login", json={"token": "wrong"}).status_code == 401
        result = c.post("/auth/login", json={"token": "wrong"})
        assert result.status_code == 429 and result.headers["retry-after"] == "60"


def test_timeline_and_advisory_history_survive_reload(client):
    for spot in ["24870", "24880", "24890"]:
        assert client.post("/api/v1/demo/tick", json={"spot": spot}).status_code == 200
    timeline = client.get("/api/v1/market/timeline?limit=2").json()
    assert [x["spot"] for x in timeline] == ["24880", "24890"]
    assert client.get("/api/v1/market/timeline?underlying=BANKNIFTY").json() == []
    client.post(
        "/api/v1/agents/explain",
        json={"agent": "trading_assistant", "question": "Review this paper portfolio"},
    )
    runs = client.get("/api/v1/agents/runs").json()
    assert len(runs) == 1
    assert runs[0]["output"]["question"] == "Review this paper portfolio"
    assert client.get("/api/v1/market/timeline?limit=501").status_code == 422


def test_newest_audit_pagination_has_no_overlap(client):
    for spot in ["24870", "24880", "24890"]:
        client.post("/api/v1/demo/tick", json={"spot": spot})
    recent = client.get("/api/v1/audit?newest=true&limit=2").json()["events"]
    older = client.get(f"/api/v1/audit?newest=true&before_id={recent[-1]['id']}").json()["events"]
    assert recent[0]["id"] > recent[1]["id"] > older[0]["id"]
    assert len(recent) + len(older) == 3


def test_public_share_preview_uses_https_origin_without_login(settings, database):
    import struct
    from html.parser import HTMLParser

    class Metadata(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = {}

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "meta":
                self.tags[attrs.get("property", attrs.get("name"))] = attrs.get("content")

    with TestClient(
        create_app(hosted(settings), database), base_url=ORIGIN.replace("https", "http")
    ) as client:
        response = client.get("/", headers={"User-Agent": "WhatsApp/2"})
        assert response.status_code == 200
        parser = Metadata()
        parser.feed(response.text)
        assert parser.tags["og:url"] == ORIGIN + "/"
        assert parser.tags["og:image"] == ORIGIN + "/static/share-card.png"
        assert parser.tags["twitter:card"] == "summary_large_image"
        assert "__PUBLIC_ORIGIN__" not in response.text
        assert TEST_KEY not in response.text
        preview = client.get(parser.tags["og:image"])
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert preview.content[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", preview.content[16:24]) == (1200, 630)
        assert client.get("/api/v1/overview").status_code == 401
