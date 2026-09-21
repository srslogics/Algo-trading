"""Read-only Kite REST adapter and pure order mapping. No live mutation methods."""

import csv
import io
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx

from optionlab.brokers.base import LiveExecutionDisabled
from optionlab.domain import Candle, InstrumentSpec, TradeIntent

IST = ZoneInfo("Asia/Kolkata")


def kite_time(value):
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    return parsed.replace(tzinfo=IST) if parsed.tzinfo is None else parsed


def parse_instruments(content: str) -> list[InstrumentSpec]:
    rows = []
    for r in csv.DictReader(io.StringIO(content)):
        if (
            r["exchange"] != "NFO"
            or r["instrument_type"] not in {"CE", "PE"}
            or r["name"] not in {"NIFTY", "BANKNIFTY"}
        ):
            continue
        rows.append(
            InstrumentSpec(
                id=f"NFO:{r['tradingsymbol']}",
                underlying=r["name"],
                option_type=r["instrument_type"],
                strike=Decimal(r["strike"]),
                expiry=r["expiry"],
                lot_size=int(r["lot_size"]),
                tick_size=Decimal(r["tick_size"]),
                instrument_token=int(r["instrument_token"]),
            )
        )
    return rows


def order_payload(intent: TradeIntent):
    exchange, symbol = intent.instrument_id.split(":", 1)
    return {
        "exchange": exchange,
        "tradingsymbol": symbol,
        "transaction_type": intent.side,
        "quantity": intent.quantity,
        "order_type": "LIMIT",
        "price": str(intent.limit_price),
        "product": "NRML",
        "validity": "DAY",
    }


class KiteReadOnly:
    def __init__(self, api_key: str, access_token: str, transport=None):
        if not api_key or not access_token:
            raise ValueError("Kite read access requires API key and access token")
        self.client = httpx.Client(
            base_url="https://api.kite.trade",
            timeout=10,
            headers={"X-Kite-Version": "3", "Authorization": f"token {api_key}:{access_token}"},
            transport=transport,
        )

    def close(self):
        self.client.close()

    def _get(self, path, params=None):
        response = self.client.get(path, params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise ValueError("Kite data request failed")
        return payload["data"]

    def instruments(self):
        response = self.client.get("/instruments/NFO")
        response.raise_for_status()
        return parse_instruments(response.text)

    def quotes(self, symbols):
        if not 1 <= len(symbols) <= 500:
            raise ValueError("Kite quote batch must contain 1–500 symbols")
        data = self._get("/quote", [("i", symbol) for symbol in symbols])
        if set(symbols) - set(data):
            raise ValueError("Kite returned an incomplete quote batch")
        return data

    def history(self, instrument_id, instrument_token, start, end, interval="minute"):
        payload = self._get(
            f"/instruments/historical/{instrument_token}/{interval}",
            {"from": start, "to": end, "oi": 1},
        )
        return [
            Candle(
                instrument_id=instrument_id,
                timestamp=kite_time(r[0]),
                interval=interval,
                open=r[1],
                high=r[2],
                low=r[3],
                close=r[4],
                volume=r[5],
                oi=r[6] if len(r) > 6 else 0,
            )
            for r in payload["candles"]
        ]

    def place_order(self, *args, **kwargs):
        raise LiveExecutionDisabled("Live execution is absent from this release")
