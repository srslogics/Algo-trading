"""Chronological snapshot replay with next-observation fills and shared entry risk."""

from datetime import timedelta
from decimal import Decimal

from optionlab.analytics.options import expiry_at
from optionlab.brokers.paper import PaperBroker
from optionlab.domain import Snapshot
from optionlab.risk.engine import AccountState, evaluate
from optionlab.strategies.momentum import STRATEGIES


def replay(snapshots: list[Snapshot], settings):
    if len(snapshots) < 3:
        raise ValueError("At least three chronological snapshots are required")
    if len({(s.underlying, s.source) for s in snapshots}) != 1:
        raise ValueError("Replay requires one underlying and data source")
    if any(a.timestamp >= b.timestamp for a, b in zip(snapshots, snapshots[1:])):
        raise ValueError("Snapshots must be strictly chronological")
    cash = settings.starting_cash
    peak = cash
    max_drawdown = Decimal(0)
    trades, curve, rejections = [], [], []
    pending = position = None
    broker = PaperBroker()
    for index, snapshot in enumerate(snapshots):
        now = snapshot.timestamp
        quotes = {q.instrument.id: q for q in snapshot.quotes}
        if position:
            q = quotes.get(position["intent"].instrument_id)
            intent = position["intent"]
            if q and 0 <= (now - q.timestamp).total_seconds() <= settings.max_quote_age_seconds:
                position["mark"] = q.bid
                change = q.bid / position["price"] - 1
                reason = None
                if change <= -intent.stop_loss_pct:
                    reason = "STOP_LOSS"
                elif change >= intent.take_profit_pct:
                    reason = "TAKE_PROFIT"
                elif now >= expiry_at(q.instrument.expiry) - timedelta(minutes=15):
                    reason = "EXPIRY_CUTOFF"
                elif now >= position["time"] + timedelta(minutes=intent.max_holding_minutes):
                    reason = "MAX_HOLDING_TIME"
                elif index == len(snapshots) - 1:
                    reason = "END_OF_DATA"
                if (
                    reason
                    and now < expiry_at(q.instrument.expiry)
                    and q.bid_quantity >= intent.quantity
                ):
                    exit_price = broker.exit_price(q, intent.quantity)
                    pnl = (
                        exit_price - position["price"]
                    ) * intent.quantity - settings.paper_fee_per_order * 2
                    cash += exit_price * intent.quantity - settings.paper_fee_per_order
                    trades.append(
                        {
                            "instrument_id": intent.instrument_id,
                            "signal_at": position["signal_at"].isoformat(),
                            "entry_at": position["time"].isoformat(),
                            "exit_at": now.isoformat(),
                            "quantity": intent.quantity,
                            "entry_price": str(position["price"]),
                            "exit_price": str(exit_price),
                            "pnl": str(pnl),
                            "reason": reason,
                        }
                    )
                    position = None
        if pending and not position:
            intent, signal_at = pending
            q = quotes.get(intent.instrument_id)
            state = AccountState(
                cash=cash,
                premium_at_risk=Decimal(0),
                loss_guard_pnl=min(Decimal(0), cash - settings.starting_cash),
                open_positions=0,
                kill_switch=False,
                stale_positions=False,
                duplicate_instrument=False,
            )
            decision = evaluate(
                intent,
                q,
                snapshot,
                state,
                signal_at + timedelta(seconds=settings.proposal_ttl_seconds),
                settings,
                now,
            )
            if decision.allowed and index < len(snapshots) - 1:
                price = broker.fill(intent, q)
                cash -= price * intent.quantity + settings.paper_fee_per_order
                position = {
                    "intent": intent,
                    "price": price,
                    "mark": q.bid,
                    "time": now,
                    "signal_at": signal_at,
                }
            elif not decision.allowed:
                rejections.append({"at": now.isoformat(), "reasons": decision.reasons})
            pending = None
        equity = cash + (position["mark"] * position["intent"].quantity if position else 0)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
        curve.append({"at": now.isoformat(), "equity": str(equity)})
        if not position and index < len(snapshots) - 1:
            intent = STRATEGIES["momentum_long_option_v1"].propose(snapshot)
            pending = (intent, now) if intent else None
    return {
        "strategy": "momentum_long_option_v1",
        "source": snapshots[0].source,
        "snapshot_count": len(snapshots),
        "starting_cash": str(settings.starting_cash),
        "ending_equity": str(equity),
        "net_pnl": str(equity - settings.starting_cash),
        "max_drawdown": str(max_drawdown),
        "trades": trades,
        "trade_count": len(trades),
        "open_positions_at_end": int(position is not None),
        "rejections": rejections,
        "equity_curve": curve,
        "assumptions": [
            "Signal at observation t; earliest fill at t+1, subject to limit and depth",
            "Bid/ask plus one adverse tick; flat configured fee per order",
            "No queue, partial fills, impact, complete taxes, or exchange calendar",
            "Loss guard is cumulative over replay; no daily reset",
            "Final liquidation requires a valid quote; remaining inventory is marked",
            "DEMO results are synthetic and are not evidence of profitability",
        ],
    }
