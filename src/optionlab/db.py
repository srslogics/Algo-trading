from contextlib import contextmanager

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from optionlab.config import Settings
from optionlab.models import Account, AuditEvent, Notification


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings
        sqlite = settings.database_url.startswith("sqlite")
        self.engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False, "timeout": 30} if sqlite else {},
            pool_pre_ping=True,
        )
        if sqlite:

            @event.listens_for(self.engine, "connect")
            def sqlite_settings(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")

        self.factory = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self, write=False):
        with self.factory() as session:
            try:
                if write and self.engine.dialect.name == "sqlite":
                    session.execute(text("BEGIN IMMEDIATE"))
                if write and self.engine.dialect.name == "postgresql":
                    # Single paper account serializes ingestion, risk evaluation, and fills.
                    session.execute(select(Account).where(Account.id == "paper").with_for_update())
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    def bootstrap(self):
        with self.transaction(write=True) as s:
            if self.engine.dialect.name == "postgresql":
                s.execute(text("SELECT pg_advisory_xact_lock(71603109)"))
            account = s.get(Account, "paper")
            if account and account.data_source != self.settings.data_source:
                raise ValueError("Database source mismatch: create a separate database per feed")
            if not account:
                s.add(
                    Account(
                        id="paper",
                        cash=self.settings.starting_cash,
                        starting_cash=self.settings.starting_cash,
                        data_source=self.settings.data_source,
                        kill_switch=False,
                    )
                )


def audit(s: Session, event: str, entity_id: str, payload: dict, actor="operator"):
    s.add(AuditEvent(event=event, entity_id=entity_id, payload=payload, actor=actor))


def notify(s: Session, topic: str, message: str):
    s.add(Notification(topic=topic, message=message))
