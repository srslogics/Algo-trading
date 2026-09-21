from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from optionlab.analytics.options import expiry_at
from optionlab.brokers.paper import PaperBroker
from optionlab.data.ingestion import latest_snapshot
from optionlab.db import audit, notify
from optionlab.domain import Snapshot, TradeIntent, aware, uid, utcnow
from optionlab.models import (
    Account,
    AuditEvent,
    MarketSnapshot,
    PaperOrder,
    Position,
    Proposal,
    RiskEvaluation,
)
from optionlab.risk.engine import AccountState, evaluate, fresh
from optionlab.strategies.momentum import STRATEGIES


class Conflict(ValueError):
    pass


def create_proposal(s, settings, strategy="momentum_long_option_v1", underlying="NIFTY"):
    snapshot = latest_snapshot(s, underlying)
    if not snapshot:
        raise ValueError("Load a market snapshot first")
    intent = STRATEGIES[strategy].propose(snapshot)
    if not intent:
        raise ValueError("No signal: strategy conditions were not satisfied")
    p = Proposal(
        id=uid(),
        account_id="paper",
        snapshot_id=snapshot.id,
        intent=intent.model_dump(mode="json"),
        status="PROPOSED",
        expires_at=utcnow() + timedelta(seconds=settings.proposal_ttl_seconds),
    )
    s.add(p)
    audit(s, "proposal.created", p.id, {"intent": p.intent, "snapshot_id": snapshot.id}, "strategy")
    s.flush()
    return p


def account_state(s, settings, instrument_id, now):
    account = s.get(Account, "paper")
    positions = s.scalars(select(Position).where(Position.status == "OPEN")).all()
    # Conservative loss guard: today's closed P&L plus all open P&L (including carryover).
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    closed = s.scalars(select(Position).where(Position.status == "CLOSED")).all()
    realized_today = sum(
        (
            p.realized_pnl
            for p in closed
            if aware(p.closed_at).astimezone(ZoneInfo("Asia/Kolkata")).date() == today
        ),
        Decimal(0),
    )
    unrealized = sum(
        ((p.mark_price - p.entry_price) * p.quantity - p.entry_fee for p in positions), Decimal(0)
    )
    return AccountState(
        cash=account.cash,
        premium_at_risk=sum(
            (p.entry_price * p.quantity + p.entry_fee for p in positions), Decimal(0)
        ),
        loss_guard_pnl=realized_today + unrealized,
        open_positions=len(positions),
        kill_switch=account.kill_switch,
        stale_positions=any(
            not fresh(p.mark_at, now, settings.max_quote_age_seconds) for p in positions
        ),
        duplicate_instrument=any(p.instrument_id == instrument_id for p in positions),
    )


def assess(s, settings, p, now=None):
    now = now or utcnow()
    intent = TradeIntent.model_validate(p.intent)
    original = Snapshot.model_validate(s.get(MarketSnapshot, p.snapshot_id).payload)
    snapshot = latest_snapshot(s, original.underlying)
    quote = next((q for q in snapshot.quotes if q.instrument.id == intent.instrument_id), None)
    result = evaluate(
        intent,
        quote,
        snapshot,
        account_state(s, settings, intent.instrument_id, now),
        p.expires_at,
        settings,
        now,
    )
    s.add(
        RiskEvaluation(
            proposal_id=p.id, snapshot_id=snapshot.id, decision=result.model_dump(mode="json")
        )
    )
    audit(
        s,
        "risk.approved" if result.allowed else "risk.rejected",
        p.id,
        {"snapshot_id": snapshot.id, **result.model_dump(mode="json")},
        "risk",
    )
    return result, quote


def execute(s, settings, proposal_id, key):
    existing = s.scalar(
        select(PaperOrder).where(
            PaperOrder.account_id == "paper", PaperOrder.idempotency_key == key
        )
    )
    if existing:
        if existing.proposal_id != proposal_id:
            raise Conflict("Idempotency key was already used for another operation")
        return existing, None
    p = s.get(Proposal, proposal_id)
    if not p:
        raise KeyError("Proposal not found")
    if p.status != "PROPOSED":
        raise Conflict("Proposal already executed")
    decision, quote = assess(s, settings, p)
    if not decision.allowed:
        notify(s, "risk.rejected", f"Paper entry rejected: {', '.join(decision.reasons)}")
        return None, decision
    intent = TradeIntent.model_validate(p.intent)
    price = PaperBroker().fill(intent, quote)
    fee = settings.paper_fee_per_order
    account = s.get(Account, "paper")
    account.cash -= price * intent.quantity + fee
    position = Position(
        id=uid(),
        account_id=account.id,
        proposal_id=p.id,
        instrument_id=intent.instrument_id,
        quantity=intent.quantity,
        entry_price=price,
        entry_fee=fee,
        mark_price=quote.bid,
        mark_at=aware(quote.timestamp),
        status="OPEN",
    )
    order = PaperOrder(
        id=uid(),
        account_id=account.id,
        proposal_id=p.id,
        position_id=position.id,
        idempotency_key=key,
        instrument_id=intent.instrument_id,
        side="BUY",
        quantity=intent.quantity,
        fill_price=price,
        fee=fee,
        reason="APPROVED_ENTRY",
    )
    p.status = "FILLED"
    s.add(position)
    s.flush()  # The order references the persisted position; both remain in one transaction.
    s.add(order)
    audit(
        s,
        "paper.order_filled",
        order.id,
        {
            "proposal_id": p.id,
            "position_id": position.id,
            "price": str(price),
            "quantity": intent.quantity,
        },
        "execution",
    )
    notify(
        s,
        "paper.fill",
        f"Bought {intent.quantity} {intent.instrument_id} at ₹{price} in paper mode.",
    )
    s.flush()
    return order, decision


def close_position(s, settings, position_id, key, reason="MANUAL_EXIT"):
    prior = s.scalar(
        select(PaperOrder).where(
            PaperOrder.idempotency_key == key, PaperOrder.account_id == "paper"
        )
    )
    if prior:
        if prior.position_id != position_id or prior.side != "SELL":
            raise Conflict("Idempotency key belongs to another operation")
        return prior
    p = s.get(Position, position_id)
    if not p:
        raise KeyError("Position not found")
    if p.status != "OPEN":
        raise Conflict("Position already closed")
    proposal = s.get(Proposal, p.proposal_id)
    original = Snapshot.model_validate(s.get(MarketSnapshot, proposal.snapshot_id).payload)
    latest = latest_snapshot(s, original.underlying)
    q = next((q for q in latest.quotes if q.instrument.id == p.instrument_id), None)
    now = utcnow()
    if (
        not q
        or not fresh(q.timestamp, now, settings.max_quote_age_seconds)
        or now >= expiry_at(q.instrument.expiry)
    ):
        raise ValueError("Exit requires a fresh, unexpired quote; position needs attention")
    price = PaperBroker().exit_price(q, p.quantity)
    fee = settings.paper_fee_per_order
    account = s.get(Account, "paper")
    account.cash += price * p.quantity - fee
    p.status = "CLOSED"
    p.closed_at = now
    p.mark_at = aware(q.timestamp)
    p.mark_price = price
    p.realized_pnl = (price - p.entry_price) * p.quantity - p.entry_fee - fee
    order = PaperOrder(
        id=uid(),
        account_id=account.id,
        position_id=p.id,
        idempotency_key=key,
        instrument_id=p.instrument_id,
        side="SELL",
        quantity=p.quantity,
        fill_price=price,
        fee=fee,
        reason=reason,
    )
    s.add(order)
    audit(
        s,
        "paper.position_closed",
        p.id,
        {"reason": reason, "pnl": str(p.realized_pnl), "order_id": order.id},
        "exit_engine",
    )
    notify(s, "paper.exit", f"{reason}: {p.instrument_id}; net P&L ₹{p.realized_pnl}.")
    s.flush()
    return order


def monitor(s, settings):
    """Called after ingestion and by a periodic process; never uses AI output."""
    now = utcnow()
    closed, attention = [], []
    for p in s.scalars(select(Position).where(Position.status == "OPEN")).all():
        proposal = s.get(Proposal, p.proposal_id)
        intent = TradeIntent.model_validate(proposal.intent)
        original = Snapshot.model_validate(s.get(MarketSnapshot, proposal.snapshot_id).payload)
        latest = latest_snapshot(s, original.underlying)
        q = next((q for q in latest.quotes if q.instrument.id == p.instrument_id), None)
        if not q or not fresh(q.timestamp, now, settings.max_quote_age_seconds):
            attention.append({"position_id": p.id, "reason": "STALE_OR_MISSING_QUOTE"})
            continue
        p.mark_price, p.mark_at = q.bid, aware(q.timestamp)
        change = q.bid / p.entry_price - 1
        reason = None
        if change <= -intent.stop_loss_pct:
            reason = "STOP_LOSS"
        elif change >= intent.take_profit_pct:
            reason = "TAKE_PROFIT"
        elif now >= expiry_at(q.instrument.expiry) - timedelta(minutes=15):
            reason = "EXPIRY_CUTOFF"
        elif now >= aware(p.opened_at) + timedelta(minutes=intent.max_holding_minutes):
            reason = "MAX_HOLDING_TIME"
        if reason:
            try:
                order = close_position(s, settings, p.id, f"auto-exit:{p.id}", reason)
                closed.append(order.id)
            except ValueError as exc:
                attention.append({"position_id": p.id, "reason": str(exc)})
    last_monitor_event = s.scalar(
        select(AuditEvent)
        .where(AuditEvent.event.in_(["monitor.attention", "monitor.recovered"]))
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    if attention:
        payload = {"positions": sorted(attention, key=lambda row: row["position_id"])}
        if not last_monitor_event or last_monitor_event.payload != payload:
            audit(s, "monitor.attention", "paper", payload, "monitor")
            notify(
                s,
                "monitor.attention",
                f"{len(attention)} open position(s) need fresh quotes or exit attention.",
            )
    elif last_monitor_event and last_monitor_event.event == "monitor.attention":
        audit(s, "monitor.recovered", "paper", {"positions": []}, "monitor")
        notify(
            s,
            "monitor.recovered",
            "Position monitoring recovered; no outstanding quote or exit issue.",
        )
    return {"closed_orders": closed, "attention": attention}
