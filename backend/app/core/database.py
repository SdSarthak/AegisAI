from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# SQLite needs check_same_thread=False; PostgreSQL ignores connect_args
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Import models to ensure they are registered on Base.metadata when other
# modules import `Base` and call `Base.metadata.create_all(...)` (some tests
# create a test sqlite engine and call create_all before app.main runs). This
# guarantees all ORM tables are present.
import app.models  # noqa: E402
