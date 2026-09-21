from sqlalchemy import select

from optionlab.db import audit
from optionlab.domain import Candle, Snapshot, aware, utcnow
from optionlab.models import HistoricalCandle, Instrument, MarketSnapshot


def latest_snapshot(s, underlying="NIFTY") -> Snapshot | None:
    row = s.scalar(
        select(MarketSnapshot)
        .where(MarketSnapshot.underlying == underlying)
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(1)
    )
    return Snapshot.model_validate(row.payload) if row else None


def ingest_snapshot(s, snapshot: Snapshot, expected_source: str):
    if snapshot.source != expected_source:
        raise ValueError("Snapshot source does not match this paper account")
    if (snapshot.timestamp - utcnow()).total_seconds() > 5:
        raise ValueError("Snapshot is in the future")
    existing = s.get(MarketSnapshot, snapshot.id)
    if existing:
        if existing.payload != snapshot.model_dump(mode="json"):
            raise ValueError("Snapshot ID already exists with different data")
        return existing
    latest = latest_snapshot(s, snapshot.underlying)
    if latest and snapshot.timestamp <= latest.timestamp:
        raise ValueError("Out-of-order snapshot; import older records as historical candles")
    for q in snapshot.quotes:
        spec = q.instrument.model_dump(mode="json")
        instrument = s.get(Instrument, q.instrument.id)
        if instrument and instrument.spec != spec:
            raise ValueError("Instrument metadata conflict; version the master explicitly")
        if not instrument:
            s.add(Instrument(id=q.instrument.id, spec=spec))
    row = MarketSnapshot(
        id=snapshot.id,
        underlying=snapshot.underlying,
        source=snapshot.source,
        timestamp=aware(snapshot.timestamp),
        payload=snapshot.model_dump(mode="json"),
    )
    s.add(row)
    audit(
        s,
        "market.snapshot_ingested",
        snapshot.id,
        {"source": snapshot.source, "quotes": len(snapshot.quotes)},
        "ingestion",
    )
    s.flush()
    return row


def ingest_candles(s, candles: list[Candle]):
    count = 0
    for candle in candles:
        row = s.scalar(
            select(HistoricalCandle).where(
                HistoricalCandle.instrument_id == candle.instrument_id,
                HistoricalCandle.interval == candle.interval,
                HistoricalCandle.timestamp == aware(candle.timestamp),
            )
        )
        if row:
            if row.payload != candle.model_dump(mode="json"):
                raise ValueError(
                    "Historical candle conflict: corrections require a versioned dataset"
                )
            continue
        s.add(
            HistoricalCandle(
                instrument_id=candle.instrument_id,
                interval=candle.interval,
                timestamp=aware(candle.timestamp),
                payload=candle.model_dump(mode="json"),
            )
        )
        s.flush()
        count += 1
    audit(s, "market.history_ingested", "history", {"inserted": count}, "ingestion")
    return count
