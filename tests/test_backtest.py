from datetime import timedelta
from decimal import Decimal

import pytest

from optionlab.backtesting.replay import replay
from optionlab.data.demo import demo_snapshot
from optionlab.domain import utcnow


def test_replay_has_no_same_observation_fill(settings):
    now = utcnow() - timedelta(minutes=5)
    snapshots = [demo_snapshot(Decimal("24870"), now + timedelta(minutes=i)) for i in range(5)]
    report = replay(snapshots, settings)
    assert report["trade_count"] == 1
    trade = report["trades"][0]
    assert trade["entry_at"] > trade["signal_at"]
    assert trade["exit_at"] > trade["entry_at"]
    assert Decimal(trade["pnl"]) < 0  # Spread, slippage, and fees on flat prices.
    assert Decimal(report["net_pnl"]) == Decimal(trade["pnl"])


def test_replay_rejects_reordered_data(settings):
    now = utcnow()
    snapshots = [demo_snapshot(now=now + timedelta(minutes=i)) for i in [0, 2, 1]]
    with pytest.raises(ValueError, match="chronological"):
        replay(snapshots, settings)


def test_demo_backtest_persists_dataset(client):
    r = client.post("/api/v1/demo/backtest")
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["source"] == "DEMO"
    assert report["snapshot_count"] == 90
    dataset = client.get(f"/api/v1/backtests/{report['id']}/dataset").json()
    assert len(dataset) == 90
    repeated = client.post("/api/v1/backtests", json={"snapshots": dataset}).json()
    assert repeated["net_pnl"] == report["net_pnl"]
    assert repeated["trades"] == report["trades"]
