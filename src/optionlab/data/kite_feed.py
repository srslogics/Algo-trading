"""Polling collector for credentialed paper research; replace transport with streaming later."""

import argparse
import time
from datetime import datetime
from decimal import Decimal

from optionlab.brokers.kite import KiteReadOnly, kite_time
from optionlab.config import Settings
from optionlab.data.ingestion import ingest_snapshot
from optionlab.db import Database
from optionlab.domain import Quote, Snapshot, utcnow
from optionlab.execution.service import monitor


def normalize_quotes(underlying, instruments, payload):
    underlying_key = "NSE:NIFTY 50" if underlying == "NIFTY" else "NSE:NIFTY BANK"
    spot = payload[underlying_key]
    quotes = []
    for i in instruments:
        raw = payload[i.id]
        bid, ask = raw["depth"]["buy"][0], raw["depth"]["sell"][0]
        if min(bid["price"], ask["price"], bid["quantity"], ask["quantity"]) <= 0:
            continue  # Missing books never become executable quotes.
        quotes.append(
            Quote(
                instrument=i,
                timestamp=kite_time(raw["timestamp"]),
                bid=Decimal(str(bid["price"])),
                ask=Decimal(str(ask["price"])),
                bid_quantity=bid["quantity"],
                ask_quantity=ask["quantity"],
                oi=raw.get("oi", 0),
                volume=raw.get("volume", 0),
            )
        )
    return Snapshot(
        source="KITE",
        timestamp=utcnow(),
        underlying=underlying,
        underlying_timestamp=kite_time(spot["timestamp"]),
        spot=Decimal(str(spot["last_price"])),
        previous_close=Decimal(str(spot["ohlc"]["close"])),
        quotes=quotes,
    )


def main():
    parser = argparse.ArgumentParser(description="Read-only Kite → paper account collector")
    parser.add_argument("--underlying", choices=["NIFTY", "BANKNIFTY"], default="NIFTY")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if settings.data_source != "KITE" or settings.demo_enabled:
        raise SystemExit("Use a separate KITE database with demo disabled")
    db = Database(settings)
    db.bootstrap()
    kite = KiteReadOnly(
        settings.kite_api_key.get_secret_value(), settings.kite_access_token.get_secret_value()
    )
    try:
        instruments = [
            i
            for i in kite.instruments()
            if i.underlying == args.underlying and i.expiry >= datetime.now().date()
        ]
        if not instruments:
            raise SystemExit("No contracts found in current master")
        nearest_expiry = min(i.expiry for i in instruments)
        instruments = [i for i in instruments if i.expiry == nearest_expiry]
        if len(instruments) > 499:
            raise SystemExit("Contract universe exceeds one quote batch; narrow the universe")
        symbols = [i.id for i in instruments] + [
            "NSE:NIFTY 50" if args.underlying == "NIFTY" else "NSE:NIFTY BANK"
        ]
        while True:
            snapshot = normalize_quotes(args.underlying, instruments, kite.quotes(symbols))
            with db.transaction(write=True) as s:
                ingest_snapshot(s, snapshot, settings.data_source)
                monitor(s, settings)
            print(f"Ingested {len(snapshot.quotes)} contracts at {snapshot.timestamp.isoformat()}")
            if args.once:
                break
            time.sleep(5)
    finally:
        kite.close()
        db.engine.dispose()


if __name__ == "__main__":
    main()
