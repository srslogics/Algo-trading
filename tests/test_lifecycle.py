from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select

from optionlab.domain import utcnow
from optionlab.models import Account, MarketSnapshot, PaperOrder, Position, Proposal


def execute(client, proposal, key="test-entry-123"):
    return client.post(
        "/api/v1/paper/orders", json={"proposal_id": proposal["id"], "idempotency_key": key}
    )


def test_end_to_end_cash_and_idempotency(client, proposal):
    initial = Decimal(client.get("/api/v1/overview").json()["cash"])
    filled = execute(client, proposal)
    assert filled.status_code == 200, filled.text
    order = filled.json()["order"]
    retry = execute(client, proposal)
    assert retry.json()["replayed"]
    assert retry.json()["order"]["id"] == order["id"]
    cash = Decimal(client.get("/api/v1/overview").json()["cash"])
    assert initial - cash == Decimal(order["fill_price"]) * order["quantity"] + Decimal(
        order["fee"]
    )
    close = client.post(
        f"/api/v1/positions/{order['position_id']}/close",
        json={"idempotency_key": "test-close-123"},
    )
    assert close.status_code == 200, close.text
    sold = close.json()
    final = Decimal(client.get("/api/v1/overview").json()["cash"])
    assert final == cash + Decimal(sold["fill_price"]) * sold["quantity"] - Decimal(sold["fee"])
    position = client.get("/api/v1/positions").json()[0]
    assert position["status"] == "CLOSED"
    assert Decimal(position["realized_pnl"]) == final - initial
    assert execute(client, proposal, "different-key-123").status_code == 409
    events = client.get("/api/v1/audit").json()["events"]
    assert {e["event"] for e in events} >= {
        "risk.approved",
        "paper.order_filled",
        "paper.position_closed",
    }


def test_concurrent_retries_fill_once(client, proposal, database):
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(lambda _: execute(client, proposal), range(8)))
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()["order"]["id"] for r in responses}) == 1
    with database.transaction() as s:
        assert len(s.scalars(select(PaperOrder)).all()) == 1
        assert len(s.scalars(select(Position)).all()) == 1


def test_concurrent_distinct_keys_cannot_double_fill(client, proposal):
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(lambda key: execute(client, proposal, key), ["key-one-123", "key-two-123"])
        )
    assert sorted(r.status_code for r in responses) == [200, 409]


def test_kill_switch_blocks_entry_but_allows_exit(client, proposal):
    client.put("/api/v1/risk/kill-switch", json={"enabled": True})
    blocked = execute(client, proposal)
    assert blocked.status_code == 409
    assert "kill_switch_clear" in blocked.json()["risk"]["reasons"]
    client.put("/api/v1/risk/kill-switch", json={"enabled": False})
    order = execute(client, proposal).json()["order"]
    client.put("/api/v1/risk/kill-switch", json={"enabled": True})
    assert (
        client.post(
            f"/api/v1/positions/{order['position_id']}/close",
            json={"idempotency_key": "exit-with-kill"},
        ).status_code
        == 200
    )


def test_risk_rechecked_after_preview(client, proposal, database):
    assert client.post(f"/api/v1/proposals/{proposal['id']}/risk").json()["allowed"]
    with database.transaction(write=True) as s:
        s.get(Account, "paper").cash = Decimal("1")
    blocked = execute(client, proposal)
    assert blocked.status_code == 409
    assert "cash_available" in blocked.json()["risk"]["reasons"]


def test_stale_data_and_expired_proposal_rejected(client, proposal, database):
    with database.transaction(write=True) as s:
        p = s.get(Proposal, proposal["id"])
        p.expires_at = utcnow() - timedelta(seconds=1)
        snapshot = s.get(MarketSnapshot, p.snapshot_id)
        payload = dict(snapshot.payload)
        payload["timestamp"] = (utcnow() - timedelta(minutes=2)).isoformat()
        payload["underlying_timestamp"] = payload["timestamp"]
        payload["quotes"] = [{**q, "timestamp": payload["timestamp"]} for q in payload["quotes"]]
        snapshot.payload = payload
    blocked = execute(client, proposal).json()["risk"]
    assert not blocked["allowed"]
    assert {"snapshot_fresh", "quote_fresh", "proposal_valid"} <= set(blocked["reasons"])


def test_automatic_stop_exit_on_ingestion(client, proposal):
    execute(client, proposal)
    tick = client.post("/api/v1/demo/tick", json={"spot": "24400"})
    assert tick.status_code == 200
    positions = client.get("/api/v1/positions").json()
    assert positions[0]["status"] == "CLOSED"
    orders = client.get("/api/v1/paper/orders").json()
    assert orders[0]["reason"] == "STOP_LOSS"


def test_stale_exit_never_fabricates_fill(client, proposal, database):
    order = execute(client, proposal).json()["order"]
    with database.transaction(write=True) as s:
        row = s.get(MarketSnapshot, proposal["snapshot_id"])
        old = (utcnow() - timedelta(minutes=2)).isoformat()
        row.payload = {
            **row.payload,
            "quotes": [{**q, "timestamp": old} for q in row.payload["quotes"]],
        }
    r = client.post(
        f"/api/v1/positions/{order['position_id']}/close",
        json={"idempotency_key": "stale-exit-123"},
    )
    assert r.status_code == 422
    assert client.get("/api/v1/positions").json()[0]["status"] == "OPEN"


def test_duplicate_instrument_entry_rejected(client, proposal):
    execute(client, proposal)
    other = client.post("/api/v1/proposals", json={}).json()
    blocked = execute(client, other, "other-proposal-123")
    assert "no_duplicate_position" in blocked.json()["risk"]["reasons"]


def test_same_key_different_proposal_conflicts(client, proposal):
    execute(client, proposal)
    other = client.post("/api/v1/proposals", json={}).json()
    assert execute(client, other).status_code == 409


def test_failed_transaction_rolls_back_cash_and_position(client, proposal, database, monkeypatch):
    import pytest

    import optionlab.execution.service as service

    original = service.audit

    def fail_after_fill(session, event, *args, **kwargs):
        if event == "paper.order_filled":
            raise RuntimeError("Injected audit persistence failure")
        return original(session, event, *args, **kwargs)

    monkeypatch.setattr(service, "audit", fail_after_fill)
    with pytest.raises(RuntimeError, match="Injected"):
        execute(client, proposal)
    with database.transaction() as s:
        assert s.get(Account, "paper").cash == Decimal("500000")
        assert s.get(Proposal, proposal["id"]).status == "PROPOSED"
        assert s.scalars(select(Position)).all() == []
        assert s.scalars(select(PaperOrder)).all() == []


def test_monitor_coalesces_repeated_attention(client, proposal, database):
    execute(client, proposal)
    with database.transaction(write=True) as s:
        row = s.get(MarketSnapshot, proposal["snapshot_id"])
        old = (utcnow() - timedelta(minutes=2)).isoformat()
        row.payload = {
            **row.payload,
            "quotes": [{**q, "timestamp": old} for q in row.payload["quotes"]],
        }
    for _ in range(3):
        result = client.post("/api/v1/monitor/run")
        assert result.status_code == 200
        assert len(result.json()["attention"]) == 1
    notes = client.get("/api/v1/notifications").json()
    assert len([n for n in notes if n["topic"] == "monitor.attention"]) == 1
