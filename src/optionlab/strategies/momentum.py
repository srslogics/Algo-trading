from decimal import Decimal
from typing import Protocol

from optionlab.analytics.options import expiry_at
from optionlab.domain import Snapshot, TradeIntent


class Strategy(Protocol):
    def propose(self, snapshot: Snapshot) -> TradeIntent | None: ...


class MomentumLongOption:
    """Illustrative signal, not a validated profitable strategy. One long option only."""

    def propose(self, snapshot):
        move = snapshot.spot / snapshot.previous_close - 1
        if abs(move) < Decimal("0.002"):
            return None
        kind = "CE" if move > 0 else "PE"
        eligible = [
            q
            for q in snapshot.quotes
            if q.instrument.option_type == kind
            and expiry_at(q.instrument.expiry) > snapshot.timestamp
        ]
        if not eligible:
            return None
        q = min(
            eligible, key=lambda q: (q.instrument.expiry, abs(q.instrument.strike - snapshot.spot))
        )
        return TradeIntent(
            instrument_id=q.instrument.id,
            quantity=q.instrument.lot_size,
            limit_price=q.ask + q.instrument.tick_size,
            signal=f"Underlying move {move * 100:.2f}% exceeds 0.20% threshold; nearest strike {kind}.",
        )


STRATEGIES = {"momentum_long_option_v1": MomentumLongOption()}
