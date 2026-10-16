"""Database engine, session factory and the `get_db` FastAPI dependency."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine manages a pool of connections to PostgreSQL; create it once per app.
# pool_pre_ping checks a connection is still alive before using it, which avoids
# errors after the database restarts or drops idle connections (common in the cloud).
# connect_timeout (seconds) makes an unreachable database fail fast instead of hanging.
engine = create_engine(
    settings.database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5}
)

# A factory that creates Session objects. A session is a short-lived unit of work:
# it tracks the objects you load or add, and sends changes to the DB on commit().
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Iterator[Session]:
    """Give each request its own session, and always close it afterwards.

    FastAPI runs the code before `yield` when a request starts and the code in
    `finally` after the response is sent, even if the endpoint raised an error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
