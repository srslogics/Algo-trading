import asyncio
import hmac
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal
from html import escape
from math import sin
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from optionlab.agents.service import AGENTS, provider
from optionlab.analytics.options import analyze
from optionlab.api.auth import COOKIE, LoginThrottle, authorized, issue_session
from optionlab.api.contracts import (
    AgentRequest,
    BacktestRequest,
    CloseRequest,
    DemoRequest,
    ErrorView,
    ExecuteRequest,
    ExecutionResult,
    HistoryRequest,
    KillSwitchRequest,
    LoginRequest,
    OrderView,
    PositionView,
    ProposalRequest,
    ProposalView,
)
from optionlab.backtesting.replay import replay
from optionlab.config import Settings
from optionlab.data.demo import demo_candles, demo_snapshot
from optionlab.data.ingestion import ingest_candles, ingest_snapshot, latest_snapshot
from optionlab.db import Database, audit, notify
from optionlab.domain import RiskDecision, Snapshot, utcnow
from optionlab.execution.service import (
    Conflict,
    assess,
    close_position,
    create_proposal,
    execute,
    monitor,
)
from optionlab.models import (
    Account,
    AgentRun,
    AuditEvent,
    BacktestRun,
    HistoricalCandle,
    MarketSnapshot,
    Notification,
    PaperOrder,
    Position,
    Proposal,
    RiskEvaluation,
)
from optionlab.risk.engine import fresh

log = logging.getLogger("optionlab")


def serialize(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def create_app(settings=None, database=None):
    settings = settings or Settings()
    if settings.environment == "render" and not settings.public_origin:
        raise ValueError(
            "Render web startup requires RENDER_EXTERNAL_URL or OPTIONLAB_PUBLIC_ORIGIN"
        )
    db = database or Database(settings)
    advisor = provider(
        settings.ai_provider, settings.openai_api_key.get_secret_value(), settings.openai_model
    )
    login_throttle = LoginThrottle()

    @asynccontextmanager
    async def lifespan(app):
        db.bootstrap()  # Schema changes are handled by Alembic, never by the web process.

        def monitor_once():
            with db.transaction(write=True) as s:
                monitor(s, settings)

        async def monitor_loop():
            while True:
                await asyncio.sleep(5)
                try:
                    await asyncio.to_thread(monitor_once)
                except Exception:
                    log.error("Position monitor failed; inspect service and database health")

        task = asyncio.create_task(monitor_loop())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        db.engine.dispose()

    app = FastAPI(
        title="Murarka Capital API",
        version="0.2.0",
        lifespan=lifespan,
        description="Paper-only modular options platform. All monetary values are decimal strings.",
    )
    app.state.db, app.state.settings = db, settings

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        client = request.client.host if request.client else ""
        if not settings.auth_required and (
            client not in {"127.0.0.1", "::1", "testclient"}
            or request.url.hostname not in {"localhost", "127.0.0.1", "::1", "testserver"}
        ):
            return JSONResponse(
                {"error": "local_only", "message": "Enable authentication for remote access"}, 403
            )
        if (
            settings.public_origin
            and request.url.path != "/healthz"
            and request.url.hostname != urlsplit(settings.public_origin).hostname
        ):
            return JSONResponse(
                {"error": "host_rejected", "message": "Use the configured workspace address"}, 403
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            expected_origin = settings.public_origin or str(request.base_url).rstrip("/")
            cookie_request = bool(request.cookies.get(COOKIE)) and not request.headers.get(
                "authorization"
            )
            if (origin and origin != expected_origin) or (cookie_request and not origin):
                return JSONResponse({"error": "origin_rejected"}, 403)
        if request.url.path.startswith("/api/"):
            if not authorized(request, settings):
                return JSONResponse({"error": "unauthorized"}, 401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.public_origin.startswith("https://"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Cache-Control"] = "no-store"
        if request.url.path == "/" or request.url.path.startswith("/static/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
            )
        return response

    @app.get("/auth/session", tags=["session"])
    def session_status(request: Request):
        return {
            "auth_required": settings.auth_required,
            "authenticated": authorized(request, settings),
        }

    @app.post("/auth/login", tags=["session"])
    def login(body: LoginRequest, request: Request):
        if not settings.auth_required:
            return {"authenticated": True}
        if not login_throttle.allow():
            return JSONResponse(
                {
                    "error": "rate_limited",
                    "message": "Too many attempts. Please try again in a minute.",
                },
                429,
                headers={"Retry-After": "60"},
            )
        if not hmac.compare_digest(
            body.token.get_secret_value().encode(), settings.api_token.get_secret_value().encode()
        ):
            return JSONResponse(
                {
                    "error": "unauthorized",
                    "message": "That access key is not valid. Check your workspace key and try again.",
                },
                401,
            )
        response = JSONResponse({"authenticated": True})
        response.set_cookie(
            COOKIE,
            issue_session(settings.api_token.get_secret_value(), settings.session_hours),
            max_age=settings.session_hours * 3600,
            httponly=True,
            samesite="strict",
            secure=settings.public_origin.startswith("https://") or request.url.scheme == "https",
        )
        return response

    @app.post("/auth/logout", tags=["session"])
    def logout():
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(
            COOKIE,
            httponly=True,
            samesite="strict",
            secure=settings.public_origin.startswith("https://"),
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(
            {
                "error": "conflict" if isinstance(exc, Conflict) else "invalid_request",
                "message": str(exc),
            },
            409 if isinstance(exc, Conflict) else 422,
        )

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"error": "not_found", "message": str(exc).strip("'")}, 404)

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return JSONResponse(
            {
                "error": "validation_error",
                "details": [{"location": e["loc"], "message": e["msg"]} for e in exc.errors()],
            },
            422,
        )

    @app.get("/healthz", tags=["operations"])
    def health():
        with db.transaction() as s:
            s.execute(text("SELECT 1"))
        return {"status": "ok", "execution_mode": "paper", "live_execution_available": False}

    router = APIRouter(prefix="/api/v1")

    @router.get("/overview", tags=["dashboard"])
    def overview(underlying: str = "NIFTY"):
        with db.transaction() as s:
            account = s.get(Account, "paper")
            positions = s.scalars(select(Position).where(Position.status == "OPEN")).all()
            snapshot = latest_snapshot(s, underlying)
            marked_value = sum((p.mark_price * p.quantity for p in positions), Decimal(0))
            unrealized = sum(
                ((p.mark_price - p.entry_price) * p.quantity - p.entry_fee for p in positions),
                Decimal(0),
            )
            return {
                "mode": "paper",
                "source": settings.data_source,
                "ai_provider": settings.ai_provider,
                "demo_enabled": settings.demo_enabled,
                "live_execution_available": False,
                "cash": str(account.cash),
                "equity": str(account.cash + marked_value),
                "starting_cash": str(account.starting_cash),
                "unrealized_pnl": str(unrealized),
                "open_positions": len(positions),
                "kill_switch": account.kill_switch,
                "quote_age_seconds": max(0, (utcnow() - snapshot.timestamp).total_seconds())
                if snapshot
                else None,
                "data_fresh": bool(
                    snapshot and fresh(snapshot.timestamp, utcnow(), settings.max_quote_age_seconds)
                ),
                "position_marks_fresh": all(
                    fresh(p.mark_at, utcnow(), settings.max_quote_age_seconds) for p in positions
                ),
                "risk_limits": {
                    "max_trade_premium": str(settings.max_trade_premium),
                    "max_total_premium": str(settings.max_total_premium),
                    "max_daily_loss": str(settings.max_daily_loss),
                    "max_positions": settings.max_positions,
                },
                "agents": AGENTS,
                "max_quote_age_seconds": settings.max_quote_age_seconds,
                "server_time": utcnow().isoformat(),
                "paper_fee_per_order": str(settings.paper_fee_per_order),
                "total_pnl": str(account.cash + marked_value - account.starting_cash),
            }

    @router.get("/market/timeline", tags=["market"])
    def timeline(underlying: str = "NIFTY", limit: int = Query(default=120, ge=1, le=500)):
        with db.transaction() as s:
            rows = s.scalars(
                select(MarketSnapshot)
                .where(MarketSnapshot.underlying == underlying)
                .order_by(MarketSnapshot.timestamp.desc())
                .limit(limit)
            ).all()
            return [
                {
                    "id": r.id,
                    "timestamp": r.payload["timestamp"],
                    "spot": r.payload["spot"],
                    "source": r.source,
                }
                for r in reversed(rows)
            ]

    @router.post("/demo/tick", tags=["demo"], response_model=Snapshot)
    def demo_tick(body: DemoRequest):
        if not settings.demo_enabled:
            raise ValueError("Demo is disabled")
        snapshot = demo_snapshot(body.spot)
        with db.transaction(write=True) as s:
            ingest_snapshot(s, snapshot, settings.data_source)
            monitor(s, settings)
        return snapshot

    @router.post("/market/snapshots", tags=["market"])
    def ingest(body: Snapshot):
        with db.transaction(write=True) as s:
            row = ingest_snapshot(s, body, settings.data_source)
            result = monitor(s, settings)
            return {"snapshot_id": row.id, "monitor": result}

    @router.get("/market/latest", tags=["market"], response_model=Snapshot)
    def latest(underlying: str = "NIFTY"):
        with db.transaction() as s:
            snapshot = latest_snapshot(s, underlying)
            if not snapshot:
                raise KeyError("No market snapshot")
            return snapshot

    @router.get("/analytics", tags=["analytics"])
    def analytics(underlying: str = "NIFTY"):
        return analyze(latest(underlying), settings.risk_free_rate)

    @router.post("/market/history", tags=["market"])
    def history_ingest(body: HistoryRequest):
        with db.transaction(write=True) as s:
            return {"inserted": ingest_candles(s, body.candles)}

    @router.get("/market/history", tags=["market"])
    def history(instrument_id: str, limit: int = Query(default=500, ge=1, le=5000)):
        with db.transaction() as s:
            return [
                r.payload
                for r in s.scalars(
                    select(HistoricalCandle)
                    .where(HistoricalCandle.instrument_id == instrument_id)
                    .order_by(HistoricalCandle.timestamp.desc())
                    .limit(limit)
                )
            ]

    @router.post("/proposals", response_model=ProposalView, tags=["strategy"])
    def propose(body: ProposalRequest):
        with db.transaction(write=True) as s:
            return create_proposal(s, settings, body.strategy, body.underlying)

    @router.get("/proposals", response_model=list[ProposalView], tags=["strategy"])
    def proposals():
        with db.transaction() as s:
            return s.scalars(select(Proposal).order_by(Proposal.created_at.desc()).limit(50)).all()

    @router.post("/proposals/{proposal_id}/risk", tags=["risk"], response_model=RiskDecision)
    def risk(proposal_id: str):
        with db.transaction(write=True) as s:
            p = s.get(Proposal, proposal_id)
            if not p:
                raise KeyError("Proposal not found")
            if p.status != "PROPOSED":
                raise Conflict("Proposal already executed")
            return assess(s, settings, p)[0]

    @router.get("/risk/evaluations", tags=["risk"])
    def risk_evaluations():
        with db.transaction() as s:
            return [
                serialize(r)
                for r in s.scalars(
                    select(RiskEvaluation).order_by(RiskEvaluation.created_at.desc()).limit(50)
                )
            ]

    @router.put("/risk/kill-switch", tags=["risk"])
    def kill_switch(body: KillSwitchRequest):
        with db.transaction(write=True) as s:
            account = s.get(Account, "paper")
            account.kill_switch = body.enabled
            audit(s, "risk.kill_switch_changed", "paper", {"enabled": body.enabled})
            notify(
                s,
                "risk.kill_switch",
                "New entries paused" if body.enabled else "New entries enabled",
            )
        return {"enabled": body.enabled, "exits_remain_available": True}

    @router.post(
        "/paper/orders",
        tags=["paper execution"],
        response_model=ExecutionResult,
        responses={
            409: {
                "model": ExecutionResult | ErrorView,
                "description": "Rejected by risk or conflicting request",
            }
        },
    )
    def paper_order(body: ExecuteRequest):
        with db.transaction(write=True) as s:
            order, decision = execute(s, settings, body.proposal_id, body.idempotency_key)
            result = {
                "order": OrderView.model_validate(order).model_dump(mode="json") if order else None,
                "risk": decision.model_dump(mode="json") if decision else None,
                "replayed": decision is None,
            }
        return JSONResponse(result, status_code=200 if order else 409)

    @router.get("/paper/orders", response_model=list[OrderView], tags=["paper execution"])
    def orders():
        with db.transaction() as s:
            return s.scalars(
                select(PaperOrder).order_by(PaperOrder.created_at.desc()).limit(100)
            ).all()

    @router.get("/positions", response_model=list[PositionView], tags=["positions"])
    def positions():
        with db.transaction() as s:
            return s.scalars(select(Position).order_by(Position.opened_at.desc()).limit(100)).all()

    @router.post("/positions/{position_id}/close", response_model=OrderView, tags=["positions"])
    def close(position_id: str, body: CloseRequest):
        with db.transaction(write=True) as s:
            return close_position(s, settings, position_id, body.idempotency_key)

    @router.post("/monitor/run", tags=["operations"])
    def run_monitor():
        with db.transaction(write=True) as s:
            return monitor(s, settings)

    @router.get("/agents", tags=["advisory AI"])
    def agents():
        return {"agents": AGENTS, "provider": settings.ai_provider, "advisory_only": True}

    @router.get("/agents/runs", tags=["advisory AI"])
    def agent_runs():
        with db.transaction() as s:
            return [
                serialize(r)
                for r in s.scalars(select(AgentRun).order_by(AgentRun.created_at.desc()).limit(40))
            ]

    @router.post("/agents/explain", tags=["advisory AI"])
    def explain(body: AgentRequest):
        with db.transaction() as s:
            snapshot = latest_snapshot(s)
            account = s.get(Account, "paper")
            context = {
                "analytics": analyze(snapshot, settings.risk_free_rate) if snapshot else {},
                "cash": str(account.cash),
                "kill_switch": account.kill_switch,
                "open_positions": len(
                    s.scalars(select(Position).where(Position.status == "OPEN")).all()
                ),
            }
            if body.proposal_id:
                p = s.get(Proposal, body.proposal_id)
                if not p:
                    raise KeyError("Proposal not found")
                context["proposal"] = p.intent
                original = Snapshot.model_validate(s.get(MarketSnapshot, p.snapshot_id).payload)
                snapshot = latest_snapshot(s, original.underlying)
                context["analytics"] = analyze(snapshot, settings.risk_free_rate)
        # External calls run outside account/database locks. No execution tools are supplied.
        try:
            result = advisor.explain(body.agent, context, body.question)
        except Exception:
            log.warning(
                "Advisory provider request failed"
            )  # Do not log provider payloads or secrets.
            with db.transaction(write=True) as s:
                audit(s, "agent.failed", body.agent, {"provider": settings.ai_provider}, "advisory")
            return JSONResponse(
                {
                    "error": "advisory_unavailable",
                    "message": "Advisory provider failed; execution state is unchanged",
                },
                503,
            )
        with db.transaction(write=True) as s:
            s.add(
                AgentRun(
                    agent=body.agent,
                    provider=settings.ai_provider,
                    context_id=body.proposal_id or (snapshot.id if snapshot else "none"),
                    output={**result, "question": body.question},
                )
            )
            audit(
                s,
                "agent.completed",
                body.agent,
                {"provider": settings.ai_provider, "advisory_only": True},
                "advisory",
            )
        return result

    @router.get("/audit", tags=["operations"])
    def audit_events(
        after_id: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
        newest: bool = False,
        before_id: int | None = Query(default=None, ge=1),
    ):
        with db.transaction() as s:
            rows = s.scalars(
                select(AuditEvent)
                .where(AuditEvent.id > after_id)
                .where(AuditEvent.id < before_id if before_id is not None else True)
                .order_by(AuditEvent.id.desc() if newest else AuditEvent.id)
                .limit(limit)
            ).all()
            return {
                "events": [serialize(r) for r in rows],
                "next_cursor": max((r.id for r in rows), default=after_id),
            }

    @router.get("/notifications", tags=["operations"])
    def notifications():
        with db.transaction() as s:
            return [
                serialize(r)
                for r in s.scalars(
                    select(Notification).order_by(Notification.created_at.desc()).limit(50)
                )
            ]

    def save_backtest(snapshots):
        report = replay(snapshots, settings)
        with db.transaction(write=True) as s:
            row = BacktestRun(report=report, dataset=[x.model_dump(mode="json") for x in snapshots])
            s.add(row)
            s.flush()
            audit(
                s,
                "backtest.completed",
                row.id,
                {"source": report["source"], "trades": report["trade_count"]},
                "backtest",
            )
            return {"id": row.id, **report}

    @router.post("/backtests", tags=["backtesting"])
    def backtest(body: BacktestRequest):
        return save_backtest(body.snapshots)

    @router.post("/demo/backtest", tags=["demo"])
    def demo_backtest():
        if not settings.demo_enabled:
            raise ValueError("Demo is disabled")
        now = utcnow() - timedelta(minutes=90)
        snapshots = [
            demo_snapshot(
                Decimal(str(round(24870 + sin(i / 5) * 110, 2))), now + timedelta(minutes=i)
            )
            for i in range(90)
        ]
        with db.transaction(write=True) as s:
            ingest_candles(s, demo_candles(now))
        return save_backtest(snapshots)

    @router.get("/backtests", tags=["backtesting"])
    def backtests():
        with db.transaction() as s:
            return [
                {"id": r.id, "report": r.report, "created_at": r.created_at}
                for r in s.scalars(
                    select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(10)
                )
            ]

    @router.get("/backtests/{run_id}/dataset", tags=["backtesting"])
    def backtest_dataset(run_id: str):
        with db.transaction() as s:
            row = s.get(BacktestRun, run_id)
            if not row:
                raise KeyError("Backtest not found")
            return row.dataset

    app.include_router(router)
    web = Path(__file__).resolve().parents[1] / "web"
    app.mount("/static", StaticFiles(directory=web), name="static")

    @app.get("/", include_in_schema=False)
    def home(request: Request):
        origin = settings.public_origin or str(request.base_url).rstrip("/")
        html = (web / "index.html").read_text(encoding="utf-8")
        return HTMLResponse(html.replace("__PUBLIC_ORIGIN__", escape(origin, quote=True)))

    return app
