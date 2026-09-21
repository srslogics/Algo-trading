# Operating the first slice

## Configuration

Application settings use the `OPTIONLAB_` prefix. `DATABASE_URL` and `RENDER_EXTERNAL_URL` are also accepted as hosting aliases. See [Render setup](RENDER.md) for the deployment path. `.env` is ignored by Git and Docker build context. Secrets use Pydantic `SecretStr` and are never returned by the configuration API.

| Variable suffix | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./optionlab.db` | Dedicated paper database |
| `ENVIRONMENT` | local | `render` requires authentication and PostgreSQL |
| `PUBLIC_ORIGIN` | empty | Canonical browser origin; falls back to `RENDER_EXTERNAL_URL` |
| `SESSION_HOURS` | 8 | Signed browser session lifetime, 1–24 hours |
| `EXECUTION_MODE` | `paper` | The only accepted value |
| `DATA_SOURCE` | `DEMO` | Database/account feed identity: DEMO or KITE |
| `DEMO_ENABLED` | true | Enables synthetic tick/replay routes |
| `AUTH_REQUIRED` | false | False is restricted to local clients/hosts |
| `API_TOKEN` | empty | Required random 32+ characters in authenticated mode |
| `STARTING_CASH` | 500000 | Applied once when account is created; never resets existing cash |
| `MAX_TRADE_PREMIUM` | 25000 | Per-entry premium plus entry fee limit |
| `MAX_TOTAL_PREMIUM` | 100000 | Aggregate open premium exposure cap |
| `MAX_DAILY_LOSS` | 10000 | Conservative closed-today plus open-P&L loss guard |
| `MAX_POSITIONS` | 5 | Entry position cap |
| `MAX_QUOTE_AGE_SECONDS` | 60 | Freshness of snapshot, underlying, option, and position marks |
| `PROPOSAL_TTL_SECONDS` | 120 | Proposal expiration |
| `PAPER_FEE_PER_ORDER` | 20 | Illustrative flat fee, not actual tax/brokerage calculation |
| `RISK_FREE_RATE` | 0.06 | Configurable modelling assumption, not a fetched current rate |
| `AI_PROVIDER` | offline | Fixed summaries or optional `openai` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | empty | Explicit opt-in to a credentialed advisory provider |
| `KITE_API_KEY`, `KITE_ACCESS_TOKEN` | empty | Read-only client credentials; no OAuth UI yet |

Never point sample and real-data collectors at the same database. Changing `DATA_SOURCE` on an existing account fails startup. Disabling demo is mandatory with KITE. For Compose, `OPTIONLAB_DB_PASSWORD` is additionally required for PostgreSQL. The initial Compose environment intentionally starts an authenticated demo; customize the shared environment mapping explicitly to use external data or an AI provider.

## Daily local use

The Docker entry point (`python -m optionlab.server`) runs versioned Alembic migrations before starting the API and stops if they fail. When invoking Uvicorn directly, run migrations first. Use one API worker in this release. The web process runs the exit monitor every five seconds, and every accepted snapshot also invokes monitoring. The browser refreshes state every ten seconds. The default server does not create market data on its own.

The entry kill switch persists in the database across restarts. Pausing entries does not close positions. Close positions explicitly or allow the deterministic exit monitor to process fresh incoming data. Paper cash, order keys, and positions survive restarts. Do not reset the database merely to clear a failed risk check.

## Failure handling

| Condition | Current behavior | Operator action |
| --- | --- | --- |
| Feed stopped/stale | Entry rejected; stale exits left open; attention audit/inbox event | Restore feed and inspect held contracts |
| Different snapshot payload reuses an ID | Ingestion rejected | Fix producer's event IDs |
| Contract master conflict | Ingestion rejected | Resolve and version metadata explicitly |
| Missing bid depth/expired contract | No invented exit fill | Inspect and implement correct settlement/recovery workflow |
| Agent provider unavailable | 503 and audit event; portfolio unchanged | Restore provider or return to offline summaries |
| Duplicate execution request | Same fill returned, or conflict for different operation | Reuse the same idempotency key after ambiguous responses |
| Risk preview becomes obsolete | Execution reruns checks and may reject | Review a new proposal against current data |
| Database write failure | Transaction rollback | Restore DB health; retry using the same request key |
| API process stopped | Monitoring stops | Restart and restore fresh data; an independent supervisor is future work |

Repeated unchanged monitoring issues are coalesced into one attention event; recovery creates a new event. Logs intentionally omit model payloads and provider exception details. A real operations deployment still needs structured correlation IDs, metrics, alert delivery, log retention and a dedicated monitor health signal.

## Database and reproducibility

Use Alembic migrations; the running API never auto-creates or silently changes tables. The initial revision is frozen, not computed from the current model at upgrade time. `alembic check` detects model/schema drift. Backtest datasets can be downloaded from `/api/v1/backtests/{id}/dataset` and submitted unchanged for identical replay results under the same settings and code version.

For a local SQLite backup, stop writes and use SQLite's backup facility; copying only the `.db` file while WAL writes are active may omit transactions. PostgreSQL requires tested backup and restore procedures before any operational use. These files are not included as preconfigured backup infrastructure.

## Before a networked deployment

The supplied token boundary is for a single trusted operator. Signed browser sessions are supplied. Introduce OIDC, RBAC, per-account authorization and scoped credentials before adding customers. Terminate TLS, set explicit allowed hosts/origins, request size and rate limits, and keep PostgreSQL private. Use a secret manager for deployed credentials, least-privilege DB roles, separate demo/paper/live infrastructure, and append-only external audit storage. Do not assume local audit rows are tamper-proof against database administrators.

The first slice does not enforce exchange holidays, trading sessions, expiry settlement, or current broker/exchange algo onboarding requirements. Those integrations are part of the live-readiness milestone. Their current requirements must be verified with the broker and exchange when that work starts. The code supplied here cannot place real orders.
