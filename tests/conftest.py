"""Shared pytest setup, loaded automatically before any test module."""

import os

# Settings are read when the app is imported, so set these first. Tests always
# use the separate ecom_test database, never the development one, even if a
# developer's .env or shell has DATABASE_URL set (environment variables take
# priority over .env). CI can point elsewhere with TEST_DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ecom_test"
)
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters-long")

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import engine, get_db
from app.main import app

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """Bring the test database schema up to date once per test run.

    Using the real migrations (not create_all) also tests that they work.
    """
    try:
        command.upgrade(Config(str(ALEMBIC_INI)), "head")
    except OperationalError as error:
        pytest.exit(
            f"Test database is not reachable ({error.orig}). "
            "Start it with: docker start ecom-db",
            returncode=1,
        )


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Give each test a session whose changes are all rolled back afterwards.

    The test runs inside an outer transaction. When app code calls commit(), it
    only commits a SAVEPOINT inside that transaction, so nothing is saved
    permanently and every test starts with an empty database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """Provide a test client whose requests use the test's rolled-back session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    # Dependency override: wherever an endpoint asks for get_db, FastAPI
    # calls override_get_db instead.
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
