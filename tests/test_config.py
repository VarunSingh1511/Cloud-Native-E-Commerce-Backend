"""Tests for loading settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings

VALID_KEY = "0123456789abcdef0123456789abcdef"


def test_env_file_may_contain_variables_for_other_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Real environment variables win over .env, so remove the test ones here
    # to make Settings read this file.
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.delenv("SECRET_KEY")
    # .env is shared with Docker Compose, which has its own variables.
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL=postgresql+psycopg://u:p@localhost/db\n"
        f"SECRET_KEY={VALID_KEY}\n"
        f"POSTGRES_PASSWORD=compose-only\n"
    )

    settings = Settings(_env_file=env_file)

    assert settings.database_url == "postgresql+psycopg://u:p@localhost/db"


def test_short_secret_key_is_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(database_url="postgresql+psycopg://u:p@localhost/db", secret_key="too-short")
