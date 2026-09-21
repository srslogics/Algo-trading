# OptionLab

A runnable, paper-first foundation for an AI-assisted Indian options platform. The first vertical slice is complete: **snapshot → analytics → deterministic proposal → risk checks → simulated fill → position monitoring and exits → audit and notifications**, with a working web dashboard and historical replay.

This is a development foundation with production-oriented boundaries, not a production trading service. Live order placement is deliberately absent. There is no environment setting or API route that enables it.

## Deploy on Render

Use the included [Render deployment guide](docs/RENDER.md) and [Blueprint](render.yaml). They configure a private paper workspace, persistent PostgreSQL, automatic migrations, HTTPS-aware sessions, and the correct runtime port. The Blueprint uses paid resources; review the cost in Render before creating them.

## Run locally

Requires Python 3.12 or 3.13. Python 3.13 is the tested runtime. Run these commands from this repository:

```sh
make install
cp .env.example .env
make run
```

Open [the dashboard](http://127.0.0.1:8000), [API documentation](http://127.0.0.1:8000/docs), or [health check](http://127.0.0.1:8000/healthz). No credentials are needed. Keep the default server bound to `127.0.0.1`.

On systems without Make:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/alembic upgrade head
.venv/bin/uvicorn optionlab.api.app:create_app --factory --host 127.0.0.1 --port 8000 --no-proxy-headers
```

## Try the vertical slice

1. Select **Update sample market**. Inspect the option chain, IV, Greeks, OI, and quote age.
2. Select **New proposal**. The sample strategy chooses one long call or put from deterministic underlying momentum. Read the signal and risk assessment.
3. Select **Review paper order → Confirm paper order**. The backend reruns all checks inside a locked account transaction, debits paper cash, and records the fill and position.
4. Inspect **Portfolio**. Close the position explicitly, or load a substantially lower sample spot to exercise a long-call stop. Exit rules also run every five seconds while the server is running.
5. Inspect all four **advisory agents**, ask the assistant, run a sample backtest, and read the audit trail and notifications.

Sample quotes become stale after 60 seconds; refresh the sample tick before executing. Proposals expire after 120 seconds. Sample data does not advance automatically. Charts load stored observations, and saved agent summaries and backtest reports remain available after refresh. Markets includes strike, expiry, call/put filters and CSV export. Quick navigation is available with ⌘K / Ctrl K; appearance can be switched between light and dark.

**The demo is fictional.** Its contract names, expiry dates, lot size of 75, prices, and OI are generated fixtures, not assertions about current NSE specifications. The demo runs outside exchange hours. The strategy is illustrative and has not been validated for profitability.

## What is implemented

| Area | First-slice behavior |
| --- | --- |
| Market ingestion | Validated snapshot ingress, chronological checks, deduplication, independent underlying/option timestamps, persistent candles |
| Indian options | NIFTY/BANKNIFTY schema; instrument-derived lots, ticks, expiry, strike, CE/PE; dashboard initially focuses on NIFTY |
| Analytics | Underlying change, chain OI ratio, bid/ask midpoint IV, Black–Scholes delta/gamma/theta/vega |
| Strategy | Versioned `momentum_long_option_v1`; one long option, whole lots, typed intent |
| Four agents | Market Research, Options Analyst, Strategy Reasoning, Trading Assistant; offline summaries and optional OpenAI provider |
| Risk | 24 checks with available quotes, including freshness, expiry, premium, cash, daily loss guard, positions, depth, tick/lot alignment, kill switch |
| Paper execution | Transactional fills, persistent idempotency keys, bid/ask slippage, illustrative fees, position P&L |
| Exits | Stop loss, take profit, holding-time limit, expiry cutoff, manual close; stale/unavailable books require attention |
| Broker architecture | Execution protocol; functioning read-only Kite instruments/quotes/history client; pure Kite limit-order mapping; submission always raises |
| Backtesting | Same strategy and entry checks over chronological option snapshots; earliest fill at next observation; persisted input dataset and report |
| Dashboard | Account, chain, proposals, positions, four agents, natural-language question input, replay results, inbox and audit |
| Operations | SQLite locally, PostgreSQL-compatible models and Compose configuration, Alembic migration, health check, local/authenticated boundary, tests, CI |

Offline agents return fixed, clearly labelled summaries. Real language-model inference requires explicit configuration. The market research role does not yet fetch news. AI explanations are optional and never influence risk approval, order quantity, or fills.

## Project map

```text
src/optionlab/
  domain.py           Validated immutable contracts and Decimal types
  config.py           Environment settings; paper-only mode
  models.py, db.py    Persistence, transactions, account locks
  data/               Demo generator, ingestion, read-only Kite collector
  analytics/          IV and Greeks
  strategies/         Deterministic strategy protocol and registry
  agents/             Exactly four advisory roles and provider boundary
  risk/               Pure deterministic risk policy
  brokers/            Paper fills, broker protocol, read-only Kite adapter
  execution/          Proposals, risk assessment, fills, monitoring, exits
  backtesting/        Chronological snapshot replay
  api/                Versioned FastAPI routes and request/response schemas
  web/                Responsive dashboard, served by the API
migrations/           Initial schema and migration runner
tests/                Analytics, controls, concurrency, replay and integration tests
docs/                 Architecture, API, operations, delivery status, OpenAPI
scripts/              OpenAPI export and local end-to-end smoke check
```

## Optional model connection

In your untracked `.env`, set `OPTIONLAB_AI_PROVIDER=openai`, `OPTIONLAB_OPENAI_API_KEY`, and an explicit `OPTIONLAB_OPENAI_MODEL` available to your account, then restart. No model or key is assumed. The adapter uses the Responses API with `store=False`, a timeout, a bounded output, no tools, and no automatic retries. Provider failures return 503 and do not alter execution state. Supplied market context, paper-account state, and the question are sent to that provider when you request an explanation. See [the official Responses guide](https://developers.openai.com/api/docs/guides/migrate-to-responses).

## Optional real market data, still paper-only

Use a **separate database** and configure `OPTIONLAB_DATA_SOURCE=KITE`, `OPTIONLAB_DEMO_ENABLED=false`, `OPTIONLAB_KITE_API_KEY`, and `OPTIONLAB_KITE_ACCESS_TOKEN`. Run migrations and restart the API for that database. Then start the collector in another terminal:

```sh
.venv/bin/python -m optionlab.data.kite_feed --underlying NIFTY
```

The collector loads current contract metadata and polls a bounded quote batch every five seconds. It stops on missing data, authentication, HTTP, or validation errors rather than concealing a failed feed. `--once` performs one batch. No authenticated broker request was made during development. OAuth login, token renewal, resilient WebSocket streaming, and session/calendar enforcement remain the next integration milestone.

Contract metadata and exchange/symbol identifiers follow [Kite's instruments and quotes contract](https://kite.trade/docs/connect/v3/market-quotes/). The adapter also supports [historical candles](https://kite.trade/docs/connect/v3/historical/). Archived expired option chains need a suitable retained/licensed dataset; the included client does not manufacture them from underlying OHLC.

## Verification and deployment

```sh
make test
make lint
npm test  # Node.js 20+; helper tests need no npm dependencies
.venv/bin/python scripts/paper_smoke.py
.venv/bin/python scripts/export_openapi.py
```

The smoke script needs a running fresh demo account without an existing position in the selected contract. It creates and closes a paper position. Tests use isolated temporary databases.

For PostgreSQL, set a generated `OPTIONLAB_DB_PASSWORD` and a random 32+ character `OPTIONLAB_API_TOKEN` in `.env`, then `docker compose up --build`. Use a URL-safe database password (for example a generated hexadecimal string). Compose requires these values, runs migrations first, enables API authentication, and exposes only a loopback port. The sign-in screen exchanges the operator key for a signed HttpOnly browser session. The key is not saved in browser storage. PostgreSQL/Compose is supplied but was not runtime-tested because Docker was unavailable.

Read [architecture and data models](docs/ARCHITECTURE.md), [API contracts](docs/API.md), [operating guide](docs/OPERATIONS.md), and [delivery status and next milestones](docs/DELIVERY.md) before extending the system. The versioned machine-readable contract is [OpenAPI JSON](docs/openapi.json).
