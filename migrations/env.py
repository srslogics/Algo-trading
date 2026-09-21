from alembic import context
from sqlalchemy import create_engine, pool, text

from optionlab.config import Settings
from optionlab.models import Base

config = context.config
url = Settings().database_url
if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        postgres = connection.dialect.name == "postgresql"
        if postgres:
            # Serialize deployment/startup migration runners on the same database.
            # Session poolers preserve this session lock across the migration transaction.
            connection.execute(text("SELECT pg_advisory_lock(71603110)"))
            connection.commit()
        try:
            context.configure(
                connection=connection, target_metadata=Base.metadata, compare_type=True
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            if postgres:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(71603110)"))
                connection.commit()
    engine.dispose()
