from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4, allow_inf_nan=False)]
PositiveMoney = Annotated[
    Decimal, Field(gt=0, max_digits=18, decimal_places=4, allow_inf_nan=False)
]


def utcnow() -> datetime:
    return datetime.now(UTC)


def uid() -> str:
    return str(uuid4())


def aware(value: datetime) -> datetime:
    # SQLite does not retain timezone metadata; persisted timestamps are always UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InstrumentSpec(Contract):
    id: str = Field(pattern=r"^NFO:[A-Z0-9_-]{1,60}$")
    underlying: Literal["NIFTY", "BANKNIFTY"]
    option_type: Literal["CE", "PE"]
    strike: PositiveMoney
    expiry: date
    lot_size: int = Field(gt=0, le=10000)
    tick_size: PositiveMoney
    instrument_token: int | None = Field(default=None, gt=0)


class Quote(Contract):
    instrument: InstrumentSpec
    timestamp: AwareDatetime
    bid: PositiveMoney
    ask: PositiveMoney
    bid_quantity: int = Field(ge=0)
    ask_quantity: int = Field(ge=0)
    oi: int = Field(ge=0)
    volume: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_book(self):
        if self.ask < self.bid:
            raise ValueError("Crossed order book")
        if any(p % self.instrument.tick_size for p in (self.bid, self.ask)):
            raise ValueError("Quote prices must align with instrument tick size")
        return self


class Snapshot(Contract):
    id: str = Field(default_factory=uid, min_length=1, max_length=80)
    source: Literal["DEMO", "KITE"]
    timestamp: AwareDatetime
    underlying_timestamp: AwareDatetime
    underlying: Literal["NIFTY", "BANKNIFTY"]
    spot: PositiveMoney
    previous_close: PositiveMoney
    quotes: list[Quote] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def same_underlying(self):
        if self.underlying_timestamp > self.timestamp:
            raise ValueError("Underlying cannot be newer than the snapshot")
        if any(q.instrument.underlying != self.underlying for q in self.quotes):
            raise ValueError("Mixed underlying snapshot")
        if len({q.instrument.id for q in self.quotes}) != len(self.quotes):
            raise ValueError("Duplicate instrument in snapshot")
        if any(q.timestamp > self.timestamp for q in self.quotes):
            raise ValueError("Quote cannot be newer than the snapshot")
        return self


class Candle(Contract):
    instrument_id: str = Field(min_length=1, max_length=80)
    timestamp: AwareDatetime
    interval: Literal["minute", "5minute", "15minute", "day"] = "minute"
    open: PositiveMoney
    high: PositiveMoney
    low: PositiveMoney
    close: PositiveMoney
    volume: int = Field(ge=0)
    oi: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def valid_ohlc(self):
        if not self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high:
            raise ValueError("Invalid OHLC candle")
        return self


class TradeIntent(Contract):
    strategy: Literal["momentum_long_option_v1"] = "momentum_long_option_v1"
    instrument_id: str
    side: Literal["BUY"] = "BUY"
    quantity: int = Field(gt=0)
    limit_price: PositiveMoney
    stop_loss_pct: Decimal = Field(default=Decimal("0.20"), gt=0, lt=1)
    take_profit_pct: Decimal = Field(default=Decimal("0.30"), gt=0, le=5)
    max_holding_minutes: int = Field(default=30, ge=1, le=1440)
    signal: str


class RiskDecision(Contract):
    allowed: bool
    reasons: list[str]
    estimated_cost: Money
    checks: dict[str, bool]
