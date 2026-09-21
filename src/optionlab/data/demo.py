from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from optionlab.analytics.options import expiry_at, price_and_greeks
from optionlab.domain import Candle, InstrumentSpec, Quote, Snapshot, utcnow


def demo_snapshot(spot=Decimal("24870"), now=None):
    now = now or utcnow()
    expiry = (now + timedelta(days=7)).date()  # Synthetic expiry, not an exchange schedule.
    years = (expiry_at(expiry) - now).total_seconds() / (365 * 86400)
    tick = Decimal("0.05")
    quotes = []
    for strike in range(24600, 25201, 100):
        for kind in ("CE", "PE"):
            i = InstrumentSpec(
                id=f"NFO:DEMO{expiry:%Y%m%d}{strike}{kind}",
                underlying="NIFTY",
                option_type=kind,
                strike=Decimal(strike),
                expiry=expiry,
                lot_size=75,
                tick_size=tick,
            )
            fair = price_and_greeks(float(spot), strike, years, 0.06, 0.18, kind)["price"]
            mid = (Decimal(str(fair)) / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
            quotes.append(
                Quote(
                    instrument=i,
                    timestamp=now,
                    bid=max(tick, mid - Decimal("0.50")),
                    ask=mid + Decimal("0.50"),
                    bid_quantity=1500,
                    ask_quantity=1500,
                    oi=150000 + (25200 - strike) * 150 + (25000 if kind == "PE" else 0),
                    volume=40000 + abs(24900 - strike) * 100,
                )
            )
    return Snapshot(
        source="DEMO",
        timestamp=now,
        underlying_timestamp=now,
        underlying="NIFTY",
        spot=spot,
        previous_close=Decimal("24750"),
        quotes=quotes,
    )


def demo_candles(now=None):
    now = (now or utcnow()).replace(second=0, microsecond=0) - timedelta(hours=3)
    result = []
    for n in range(90):
        price = Decimal("200") + Decimal(n % 20) * 3 + Decimal(n // 20) * 2
        result.append(
            Candle(
                instrument_id="DEMO:OPTION_REPLAY",
                timestamp=now + timedelta(minutes=n),
                open=price,
                high=price + 4,
                low=price - 3,
                close=price + 1,
                volume=5000,
                oi=100000,
            )
        )
    return result
