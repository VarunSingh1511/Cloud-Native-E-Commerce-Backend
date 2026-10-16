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

from app.core.security import create_access_token, hash_password
from app.db.session import engine, get_db
from app.main import app
from app.models.user import User, UserRole
from tests.helpers import PASSWORD, bearer

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"

# Argon2 is deliberately slow, so hash the shared test password only once.
_PASSWORD_HASH = hash_password(PASSWORD)


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
def use_test_session(db_session: Session) -> Iterator[None]:
    """Make every request in this test use the test's rolled-back session."""

    def override_get_db() -> Iterator[Session]:
        yield db_session

    # Dependency override: wherever an endpoint asks for get_db, FastAPI
    # calls override_get_db instead.
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(use_test_session: None) -> Iterator[TestClient]:
    """An anonymous (not logged in) test client."""
    with TestClient(app) as test_client:
        yield test_client


def _client_logged_in_as(db_session: Session, email: str, role: UserRole) -> TestClient:
    """Create a user directly in the test DB and return a client sending its token."""
    user = User(email=email, hashed_password=_PASSWORD_HASH, role=role)
    db_session.add(user)
    db_session.commit()
    return TestClient(app, headers=bearer(create_access_token(user.id)))


@pytest.fixture
def admin_client(use_test_session: None, db_session: Session) -> Iterator[TestClient]:
    """A test client logged in as an ADMIN user."""
    with _client_logged_in_as(db_session, "admin@example.com", UserRole.ADMIN) as test_client:
        yield test_client


@pytest.fixture
def customer_client(use_test_session: None, db_session: Session) -> Iterator[TestClient]:
    """A test client logged in as a CUSTOMER user."""
    with _client_logged_in_as(
        db_session, "customer@example.com", UserRole.CUSTOMER
    ) as test_client:
        yield test_client
