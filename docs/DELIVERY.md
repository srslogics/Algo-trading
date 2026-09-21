# First-slice delivery and next milestones

## Delivered

The repository includes a running dashboard, modular Python backend, strict domain contracts, 12 persistent tables, a frozen initial migration, versioned API schema, environment examples, pinned dependencies, Docker/PostgreSQL deployment files, CI and automated tests.

The working flow uses generated option quotes and supports proposal creation, deterministic risk preview, transactional paper execution, repeat-safe order requests, monitoring, manual and rule-based exits, cash and P&L, notifications, audit, four advisory roles and persisted backtesting datasets. An optional OpenAI adapter and read-only Kite REST collector are implemented but do not have credentials in this project.

## Verified here

- All 45 Python tests and 4 frontend helper tests pass; the PostgreSQL integration test is skipped locally and configured as a separate CI job. They cover reference option prices and IV, money accounting, eight concurrent retries, distinct-key contention, transaction rollback, kill-switch behavior, fresh-risk reevaluation, stale data, expired proposals, stop exits, stale-exit refusal, duplicate contracts, schema validation, authentication, origin boundaries, advisory separation, mocked provider contracts, broker mapping and replay timing/reproducibility.
- Initial migration applied successfully to SQLite; Alembic reported no model drift.
- API smoke exercise created and closed a paper position and verified retry identity.
- Browser exercise loaded the sample chain, assessed a proposal, executed and closed it, and displayed a saved backtest.
- Source lint and JavaScript syntax checks passed.
- Premium responsive dashboard, keyboard navigation, order reviews, filters, exports, saved reports, and light/dark appearance added.
- Render Blueprint validated against the official JSON schema; signed session, expiry, rotation, rate limiting, HTTPS proxy, host/origin and PostgreSQL URL safeguards tested.

No paid AI request, broker login, live market request, or live order was made. PostgreSQL/Compose was not run because the local Docker daemon was unavailable. The browser's offline assistant is intentionally a fixed summary, not evidence that language-model inference was tested.

## Next milestones and acceptance criteria

| Stage | Work | Completion evidence |
| --- | --- | --- |
| 2 · Real feed foundation | Kite login/token lifecycle; WebSocket subscriptions/reconnect; heartbeat/gap detection; daily versioned instrument master; market calendars; historical options archive | Credentialed paper soak tests, reconnect/gap recovery, fresh held-contract marks, documented data rights and coverage |
| 3 · Research quality | Validate quantitative strategies; news/context connectors; agent evidence provenance and evals; volatility model improvements; complete cost model | Out-of-sample analysis, reproducible datasets, explicit assumptions, adversarial advisory tests |
| 4 · Production paper operations | PostgreSQL concurrency tests; multi-account isolation; OIDC/RBAC; independent workers; queue/outbox delivery; dashboards/alerts; backups; retention | Load tests, restart/failover drills, account-isolation tests, restore exercise and operating runbooks |
| 5 · Expanded strategy support | Defined-risk spreads, portfolio Greeks, margin and exposure models, multi-leg state and recovery | Payoff/margin reference tests and paper failure simulations for every strategy |
| 6 · Separately authorized live implementation | Current broker/exchange onboarding requirements; isolated live OMS; submission/reconciliation state machine; partial fills, cancels, rejects; kill and recovery controls | Reviewable readiness evidence and an explicit live enablement decision; never an environment-only bypass |

The next useful build step is stage 2: connect a credentialed feed to a separate paper environment and validate it through multiple market sessions. Keep the current local demo usable as a regression fixture throughout.
