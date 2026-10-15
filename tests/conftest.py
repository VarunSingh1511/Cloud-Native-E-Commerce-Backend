"""Shared pytest setup, loaded automatically before any test module."""

import os

# Settings require these values. Set them before the app is imported so tests
# never depend on a developer's local .env file. setdefault keeps any real
# values already set (for example in CI).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
