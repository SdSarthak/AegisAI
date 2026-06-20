import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.telemetry import DB_QUERY_LATENCY

logger = logging.getLogger(__name__)

try:
    import redis as redis_module
except ImportError:
    redis_module = None

# SQLite needs check_same_thread=False; PostgreSQL ignores connect_args
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args}
if settings.DATABASE_URL in {"sqlite:///:memory:", "sqlite://"}:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# -------------------------------------------------------------------
# SQLAlchemy query instrumentation
# -------------------------------------------------------------------
@event.listens_for(engine, "before_cursor_execute")
def _before_cursor_execute(
    conn, cursor, statement, parameters, context, executemany,
):
    conn._query_start = time.perf_counter()


@event.listens_for(engine, "after_cursor_execute")
def _after_cursor_execute(
    conn, cursor, statement, parameters, context, executemany,
):
    duration = time.perf_counter() - conn._query_start
    operation = statement.split(None, 1)[0].lower() if statement else "unknown"
    DB_QUERY_LATENCY.labels(operation=operation).observe(duration)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_redis_client = None


def get_redis():
    """Return a shared Redis client, or None if Redis is not configured."""
    global _redis_client
    if not settings.REDIS_URL or redis_module is None:
        return None
    if _redis_client is None:
        try:
            _redis_client = redis_module.Redis.from_url(
                settings.REDIS_URL, decode_responses=True
            )
        except Exception:
            logger.exception("Failed to connect to Redis")
            return None
    return _redis_client
