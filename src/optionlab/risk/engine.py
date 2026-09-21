from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from optionlab.analytics.options import expiry_at
from optionlab.config import Settings
from optionlab.domain import Quote, RiskDecision, Snapshot, TradeIntent, aware


@dataclass(frozen=True)
class AccountState:
    cash: Decimal
    premium_at_risk: Decimal
    loss_guard_pnl: Decimal
    open_positions: int
    kill_switch: bool
    stale_positions: bool
    duplicate_instrument: bool


def fresh(timestamp, now, max_age):
    return -5 <= (now - aware(timestamp)).total_seconds() <= max_age


def evaluate(
    intent: TradeIntent,
    quote: Quote | None,
    snapshot: Snapshot,
    state: AccountState,
    expires_at: datetime,
    settings: Settings,
    now: datetime,
) -> RiskDecision:
    estimated_cost = intent.limit_price * intent.quantity + settings.paper_fee_per_order
    checks = {
        "paper_only": settings.execution_mode == "paper",
        "source_matches": snapshot.source == settings.data_source,
        "kill_switch_clear": not state.kill_switch,
        "proposal_valid": now < aware(expires_at),
        "snapshot_fresh": fresh(snapshot.timestamp, now, settings.max_quote_age_seconds),
        "underlying_fresh": fresh(
            snapshot.underlying_timestamp, now, settings.max_quote_age_seconds
        ),
        "position_marks_fresh": not state.stale_positions,
        "long_only": intent.side == "BUY",
        "cash_available": estimated_cost <= state.cash,
        "trade_premium_limit": estimated_cost <= settings.max_trade_premium,
        "portfolio_premium_limit": state.premium_at_risk + estimated_cost
        <= settings.max_total_premium,
        "daily_loss_limit": state.loss_guard_pnl > -settings.max_daily_loss,
        "position_count": state.open_positions < settings.max_positions,
        "no_duplicate_position": not state.duplicate_instrument,
        "instrument_present": quote is not None,
    }
    if quote:
        checks.update(
            {
                "instrument_matches": quote.instrument.id == intent.instrument_id,
                "quote_fresh": fresh(quote.timestamp, now, settings.max_quote_age_seconds),
                "before_expiry_cutoff": now + timedelta(minutes=15)
                < expiry_at(quote.instrument.expiry),
                "whole_lots": intent.quantity % quote.instrument.lot_size == 0,
                "tick_alignment": intent.limit_price % quote.instrument.tick_size == 0,
                "spread_limit": (quote.ask - quote.bid) / quote.ask <= Decimal("0.05"),
                "open_interest": quote.oi > 0,
                "displayed_depth": quote.ask_quantity >= intent.quantity,
                "within_limit": quote.ask + quote.instrument.tick_size <= intent.limit_price,
            }
        )
    reasons = [key for key, ok in checks.items() if not ok]
    return RiskDecision(
        allowed=not reasons, reasons=reasons, estimated_cost=estimated_cost, checks=checks
    )
