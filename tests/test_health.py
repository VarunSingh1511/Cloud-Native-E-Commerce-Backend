"""Tests for the health endpoints."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


class UnreachableDatabaseSession:
    """Stands in for a session whose database is down."""

    def execute(self, *args: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


@pytest.fixture
def client_with_database_down() -> Iterator[TestClient]:
    """A client whose requests get a session that cannot reach the database."""

    def broken_get_db() -> Iterator[UnreachableDatabaseSession]:
        yield UnreachableDatabaseSession()

    app.dependency_overrides[get_db] = broken_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_root_endpoint(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Cloud E-Commerce API is running"}


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}


def test_ready_when_database_is_up(client: TestClient) -> None:
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_not_ready_when_database_is_down(client_with_database_down: TestClient) -> None:
    response = client_with_database_down.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unreachable"}


def test_liveness_ignores_database_outage(client_with_database_down: TestClient) -> None:
    assert client_with_database_down.get("/health").status_code == 200
