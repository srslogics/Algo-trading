from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from optionlab.domain import Candle, Contract, RiskDecision, Snapshot, TradeIntent


class DemoRequest(Contract):
    spot: Decimal = Field(default=Decimal("24870"), ge=20000, le=30000, decimal_places=2)


class LoginRequest(Contract):
    token: SecretStr = Field(min_length=1, max_length=512)


class ProposalRequest(Contract):
    strategy: Literal["momentum_long_option_v1"] = "momentum_long_option_v1"
    underlying: Literal["NIFTY", "BANKNIFTY"] = "NIFTY"


class ExecuteRequest(Contract):
    proposal_id: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9:_-]+$")


class CloseRequest(Contract):
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[a-zA-Z0-9:_-]+$")


class KillSwitchRequest(Contract):
    enabled: bool


class AgentRequest(Contract):
    agent: Literal["market_research", "options_analyst", "strategy_reasoning", "trading_assistant"]
    question: str = Field(default="", max_length=2000)
    proposal_id: str | None = None


class HistoryRequest(Contract):
    candles: list[Candle] = Field(min_length=1, max_length=5000)


class BacktestRequest(Contract):
    snapshots: list[Snapshot] = Field(min_length=3, max_length=1000)


class Row(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProposalView(Row):
    id: str
    snapshot_id: str
    intent: TradeIntent
    status: str
    created_at: datetime
    expires_at: datetime


class OrderView(Row):
    id: str
    proposal_id: str | None
    position_id: str
    idempotency_key: str
    instrument_id: str
    side: str
    quantity: int
    fill_price: Decimal
    fee: Decimal
    status: str
    reason: str
    created_at: datetime


class PositionView(Row):
    id: str
    proposal_id: str
    instrument_id: str
    quantity: int
    entry_price: Decimal
    mark_price: Decimal
    mark_at: datetime
    entry_fee: Decimal
    realized_pnl: Decimal
    status: str
    opened_at: datetime
    closed_at: datetime | None


class ExecutionResult(Contract):
    order: OrderView | None
    risk: RiskDecision | None
    replayed: bool


class ErrorView(Contract):
    error: str
    message: str
