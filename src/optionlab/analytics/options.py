"""European Black–Scholes diagnostics; no execution dependencies."""

from datetime import datetime, time
from math import erf, exp, isfinite, log, pi, sqrt
from zoneinfo import ZoneInfo

from optionlab.domain import Snapshot


def cdf(x):
    return (1 + erf(x / sqrt(2))) / 2


def price_and_greeks(spot, strike, years, rate, volatility, kind):
    if (
        kind not in {"CE", "PE"}
        or not all(isfinite(x) for x in (spot, strike, years, rate, volatility))
        or min(spot, strike, years, volatility) <= 0
    ):
        raise ValueError("Positive, finite inputs and an unexpired CE/PE contract required")
    d1 = (log(spot / strike) + (rate + volatility**2 / 2) * years) / (volatility * sqrt(years))
    d2 = d1 - volatility * sqrt(years)
    density = exp(-d1 * d1 / 2) / sqrt(2 * pi)
    discounted = strike * exp(-rate * years)
    if kind == "CE":
        price = spot * cdf(d1) - discounted * cdf(d2)
        delta = cdf(d1)
        theta = -spot * density * volatility / (2 * sqrt(years)) - rate * discounted * cdf(d2)
    else:
        price = discounted * cdf(-d2) - spot * cdf(-d1)
        delta = cdf(d1) - 1
        theta = -spot * density * volatility / (2 * sqrt(years)) + rate * discounted * cdf(-d2)
    return {
        "price": price,
        "delta": delta,
        "gamma": density / (spot * volatility * sqrt(years)),
        "vega": spot * density * sqrt(years) / 100,
        "theta": theta / 365,
    }


def implied_volatility(premium, spot, strike, years, rate, kind):
    if years <= 0 or not isfinite(premium) or premium <= 0:
        return None
    discounted = strike * exp(-rate * years)
    lower = max(0, spot - discounted) if kind == "CE" else max(0, discounted - spot)
    upper = spot if kind == "CE" else discounted
    if not lower < premium < upper:
        return None
    lo, hi = 0.0001, 5.0
    if price_and_greeks(spot, strike, years, rate, hi, kind)["price"] < premium:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        price = price_and_greeks(spot, strike, years, rate, mid, kind)["price"]
        if abs(price - premium) < 1e-7:
            return mid
        if price > premium:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def expiry_at(expiry):
    return datetime.combine(expiry, time(15, 30), ZoneInfo("Asia/Kolkata"))


def analyze(snapshot: Snapshot, rate=0.06):
    chain = []
    for q in snapshot.quotes:
        i = q.instrument
        years = (expiry_at(i.expiry) - snapshot.timestamp).total_seconds() / (365 * 86400)
        mid = float((q.bid + q.ask) / 2)
        iv = implied_volatility(
            mid, float(snapshot.spot), float(i.strike), years, rate, i.option_type
        )
        greeks = (
            price_and_greeks(float(snapshot.spot), float(i.strike), years, rate, iv, i.option_type)
            if iv
            else None
        )
        chain.append(
            {
                "instrument_id": i.id,
                "strike": str(i.strike),
                "type": i.option_type,
                "expiry": i.expiry.isoformat(),
                "bid": str(q.bid),
                "ask": str(q.ask),
                "oi": q.oi,
                "volume": q.volume,
                "iv": iv,
                "greeks": greeks,
                "quality": "OK" if iv else "IV_UNAVAILABLE",
            }
        )
    call_oi = sum(q.oi for q in snapshot.quotes if q.instrument.option_type == "CE")
    put_oi = sum(q.oi for q in snapshot.quotes if q.instrument.option_type == "PE")
    return {
        "snapshot_id": snapshot.id,
        "underlying": snapshot.underlying,
        "source": snapshot.source,
        "as_of": snapshot.timestamp.isoformat(),
        "spot": str(snapshot.spot),
        "change_pct": float((snapshot.spot / snapshot.previous_close - 1) * 100),
        "put_call_oi_ratio": put_oi / call_oi if call_oi else None,
        "chain": chain,
        "assumptions": {
            "model": "Black–Scholes, European, zero dividend yield",
            "risk_free_rate": rate,
            "theta": "per calendar day",
            "vega": "per 1 volatility percentage point",
        },
    }
