# Working in OptionLab

Keep the first release paper-only. Do not add a live order route, live broker mutation, or configuration switch as incidental work. Treat any future live-execution implementation as a separate explicit scope.

AI modules receive serialized read-only context and return advisory text. They must not import execution services, risk configuration mutation, or broker credentials. The strategy emits a typed intent, and risk is recomputed in the same account transaction that creates a paper fill.

Money uses Decimal; timestamps are UTC with timezone-aware ingress; display time is Asia/Kolkata. Load contract expiry, lot size, tick size, and identifiers from a versioned instrument master. Demo metadata is fictional.

Changes to database models require an Alembic revision. Preserve idempotency and atomicity across cash, orders, positions, notifications, and audit events. Run the relevant tests and lint after changes. Do not claim live broker or model integration has been verified without actually exercising the credentialed integration.
