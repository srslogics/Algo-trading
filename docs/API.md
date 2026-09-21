# API contracts · v1

The canonical schema is [openapi.json](openapi.json), generated from the application. Interactive documentation is served at `/docs`. Paths below are under `/api/v1` unless stated otherwise. Responses use decimal strings for money. Timestamps represent UTC; ingress requires an explicit offset. The paper account is fixed; account IDs from clients are not accepted.

## Operations

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/healthz` (no v1 prefix) | Database reachability and paper-only capability |
| GET | `/overview` | Cash, equity, mark freshness, source, limits, agent registry |
| POST | `/demo/tick` | Optional `spot` decimal string; creates a fresh synthetic snapshot and runs exits |
| POST | `/market/snapshots` | Strict `Snapshot`; idempotent by id; rejects changed payload or out-of-order data |
| GET | `/market/timeline?underlying=NIFTY&limit=120` | Stored observations in chronological order, up to 500 |
| GET | `/market/latest?underlying=NIFTY` | Latest accepted snapshot |
| POST | `/market/history` | `{ "candles": [...] }`, up to 5,000; duplicate unchanged candles skipped |
| GET | `/market/history?instrument_id=...&limit=500` | Newest-first stored candles |
| GET | `/analytics?underlying=NIFTY` | Underlying metrics, option chain, IV, Greeks, assumptions |
| POST | `/proposals` | Strategy id and underlying; creates typed intent if signal exists |
| GET | `/proposals` | Latest 50 proposals |
| POST | `/proposals/{id}/risk` | Persisted preview; gives no lasting execution permission |
| GET | `/risk/evaluations` | Latest 50 decisions and their input snapshot IDs |
| PUT | `/risk/kill-switch` | `{ "enabled": true }`; pauses entries, permits exits |
| POST | `/paper/orders` | Proposal id and idempotency key; reevaluates then fills or rejects |
| GET | `/paper/orders` | Latest 100 simulated fills |
| GET | `/positions` | Latest 100 positions, marks, fees and realized P&L |
| POST | `/positions/{id}/close` | Idempotency key; closes at valid simulated bid-side price |
| POST | `/monitor/run` | Runs deterministic exits; returns closures and attention |
| GET | `/agents` | Exactly four roles and configured provider |
| GET | `/agents/runs` | Latest 40 saved advisory questions and responses |
| POST | `/agents/explain` | Role, question, optional proposal id; returns advisory text |
| GET | `/audit?after_id=0&limit=100` | Ascending audit events and next cursor; `newest=true` reverses order, `before_id` pages toward older events |
| GET | `/notifications` | Latest 50 locally persisted inbox messages |
| POST | `/backtests` | 3–1,000 chronological snapshots; saves dataset and report |
| POST | `/demo/backtest` | Synthetic 90-observation replay, isolated from paper portfolio |
| GET | `/backtests` | Latest 10 reports |
| GET | `/backtests/{id}/dataset` | Exact original input snapshots for reproducibility |

## Complete paper flow

```http
POST /api/v1/demo/tick
Content-Type: application/json

{"spot":"24870"}
```

```http
POST /api/v1/proposals
Content-Type: application/json

{"strategy":"momentum_long_option_v1","underlying":"NIFTY"}
```

The server returns a proposal ID, snapshot ID, status, creation/expiry timestamps, and an intent:

```json
{
  "strategy": "momentum_long_option_v1",
  "instrument_id": "NFO:DEMO2026092724900CE",
  "side": "BUY",
  "quantity": 75,
  "limit_price": "239.90",
  "stop_loss_pct": "0.20",
  "take_profit_pct": "0.30",
  "max_holding_minutes": 30,
  "signal": "Underlying move exceeds the configured strategy threshold."
}
```

This is an illustrative response; read the returned ID and actual values rather than reusing the example contract. The client cannot submit arbitrary quantities, limits, exits, or AI-generated intents through this release's execution API.

```http
POST /api/v1/paper/orders
Content-Type: application/json

{"proposal_id":"<returned-id>","idempotency_key":"entry:<returned-id>"}
```

Success returns `order`, `risk`, and `replayed:false`. An identical completed retry returns the same order, `risk:null`, and `replayed:true`. A rejection returns HTTP 409 with `order:null` and the full failed risk decision. Fixing the underlying condition may allow retrying a still-valid proposal because rejected requests do not reserve a fill key. Reusing a completed key for a different operation returns a conflict error.

## Feed contract

`Snapshot` includes `id`, `source` (`DEMO`/`KITE`), acquisition `timestamp`, `underlying_timestamp`, `underlying`, `spot`, `previous_close`, and `quotes`. Each quote carries its own timestamp, instrument spec, bid/ask prices, displayed quantities, OI and volume. Each instrument includes exchange:symbol identity, underlying, option type, strike, expiry, lot size, tick size and optional provider token. Snapshot acquisition time cannot be used to refresh an old underlying or option quote.

Unknown fields, NaN/Infinity, naive timestamps, duplicate symbols, crossed books and off-tick quote prices are rejected. Positive bid/ask prices are required. Zero depth is representable but cannot pass execution risk. A fresh full snapshot must still contain a held contract to mark or exit it; omitted contracts are treated as missing.

`Candle` includes instrument identity, aware timestamp, supported interval, OHLC, volume, and OI. Candles are retained for research but do not substitute for option-chain snapshots in this backtester.

## Auth and errors

Local mode permits only loopback clients and loopback hosts. Remote operation requires `OPTIONLAB_AUTH_REQUIRED=true` and a 32+ character token. API clients supply `Authorization: Bearer …` on each v1 request. Browsers exchange the key at `POST /auth/login` with `{ "token": "…" }` for a signed HttpOnly session cookie. `GET /auth/session` reports authentication state and `POST /auth/logout` clears the cookie. These three paths have no v1 prefix. Browser cookie mutations require the canonical same-origin Origin header. `OPTIONLAB_PUBLIC_ORIGIN` (or Render’s `RENDER_EXTERNAL_URL`) controls host/origin enforcement behind TLS termination. Credentials are never accepted in URLs. This is a single operator API boundary, not end-user authentication or role-based authorization.

Typical errors are 401 (missing/incorrect token), 403 (nonlocal access or foreign origin), 429 (login rate limit), 404 (missing record), 409 (risk rejection or state/idempotency conflict), 422 (invalid contract or data), and 503 (advisory provider unavailable). Unexpected server failures return a generic server error. Request validation errors exclude raw input values.

The first release uses capped recent-result endpoints for most lists; only audit has a cursor. Long-lived production clients will need paginated orders, positions, and history with retention/export policies. No WebSocket dashboard or public live-execution route exists yet.
