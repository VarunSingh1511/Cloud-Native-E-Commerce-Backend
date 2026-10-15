"""Shared pytest setup, loaded automatically before any test module."""

import os

# Settings require these values. Set them before the app is imported so tests
# never depend on a developer's local .env file. setdefault keeps any real
# values already set (for example in CI).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.products import reset_products


@pytest.fixture(autouse=True)
def restore_sample_products() -> None:
    """Ensure each test starts with the same in-memory sample data."""
    reset_products()


@pytest.fixture
def client() -> TestClient:
    """Provide a test client that calls the app in-process (no real server)."""
    return TestClient(app)
