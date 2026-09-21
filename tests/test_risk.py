from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from optionlab.data.demo import demo_snapshot
from optionlab.domain import utcnow
from optionlab.risk.engine import AccountState, evaluate
from optionlab.strategies.momentum import MomentumLongOption


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"cash": Decimal("0")}, "cash_available"),
        ({"premium_at_risk": Decimal("100000")}, "portfolio_premium_limit"),
        ({"loss_guard_pnl": Decimal("-10000")}, "daily_loss_limit"),
        ({"open_positions": 5}, "position_count"),
        ({"stale_positions": True}, "position_marks_fresh"),
    ],
)
def test_portfolio_limits(settings, changes, reason):
    now = utcnow()
    snapshot = demo_snapshot(now=now)
    intent = MomentumLongOption().propose(snapshot)
    q = next(q for q in snapshot.quotes if q.instrument.id == intent.instrument_id)
    state = AccountState(Decimal("500000"), Decimal(0), Decimal(0), 0, False, False, False)
    result = evaluate(
        intent, q, snapshot, replace(state, **changes), now + timedelta(minutes=1), settings, now
    )
    assert reason in result.reasons


def test_invalid_lot_tick_depth_and_stale_underlying(settings):
    now = utcnow()
    snapshot = demo_snapshot(now=now).model_copy(
        update={"underlying_timestamp": now - timedelta(minutes=10)}
    )
    intent = (
        MomentumLongOption()
        .propose(snapshot)
        .model_copy(update={"quantity": 1, "limit_price": Decimal("100.03")})
    )
    q = next(q for q in snapshot.quotes if q.instrument.id == intent.instrument_id).model_copy(
        update={"ask_quantity": 0}
    )
    state = AccountState(Decimal("500000"), Decimal(0), Decimal(0), 0, False, False, False)
    result = evaluate(intent, q, snapshot, state, now + timedelta(minutes=1), settings, now)
    assert {"whole_lots", "tick_alignment", "displayed_depth", "underlying_fresh"} <= set(
        result.reasons
    )
