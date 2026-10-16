"""Tests for the create_admin command-line script."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole
from app.scripts import create_admin
from app.services.users import get_user_by_email
from tests.helpers import PASSWORD, bearer, login, register


@pytest.fixture
def script_uses_test_session(monkeypatch: pytest.MonkeyPatch, db_session: Session) -> None:
    """Point the script at the rolled-back test session instead of the real database."""
    monkeypatch.setattr(create_admin, "SessionLocal", lambda: db_session)


def answer_password_prompts(monkeypatch: pytest.MonkeyPatch, *answers: str) -> None:
    """Make getpass return these answers in order instead of waiting for typing."""
    replies = iter(answers)
    monkeypatch.setattr(create_admin.getpass, "getpass", lambda prompt: next(replies))


def test_creates_new_admin_who_can_log_in(
    monkeypatch: pytest.MonkeyPatch, script_uses_test_session: None, client: TestClient
) -> None:
    answer_password_prompts(monkeypatch, PASSWORD, PASSWORD)

    create_admin.main(["Boss@Example.com"])

    token = login(client, email="boss@example.com")
    me = client.get("/users/me", headers=bearer(token)).json()
    assert me["role"] == "ADMIN"


def test_promotes_existing_user_without_asking_for_password(
    script_uses_test_session: None, client: TestClient, db_session: Session
) -> None:
    register(client, email="alice@example.com")

    create_admin.main(["alice@example.com"])  # getpass would fail if called

    user = get_user_by_email(db_session, "alice@example.com")
    assert user is not None
    assert user.role == UserRole.ADMIN


def test_mismatched_passwords_abort(
    monkeypatch: pytest.MonkeyPatch, script_uses_test_session: None, db_session: Session
) -> None:
    answer_password_prompts(monkeypatch, PASSWORD, "something-else")

    with pytest.raises(SystemExit, match="Passwords do not match"):
        create_admin.main(["boss@example.com"])
    assert get_user_by_email(db_session, "boss@example.com") is None


def test_short_password_is_rejected(
    monkeypatch: pytest.MonkeyPatch, script_uses_test_session: None, db_session: Session
) -> None:
    answer_password_prompts(monkeypatch, "short", "short")

    with pytest.raises(SystemExit, match="Invalid input"):
        create_admin.main(["boss@example.com"])
    assert get_user_by_email(db_session, "boss@example.com") is None
