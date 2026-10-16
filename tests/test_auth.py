"""Tests for registration, login and GET /users/me."""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User
from app.services.users import get_user_by_email
from tests.helpers import PASSWORD, bearer, login, register

# --- Registration ---


def test_register_creates_customer(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"email": "alice@example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "CUSTOMER"
    assert set(body) == {"id", "email", "role", "created_at"}  # no password fields


def test_register_ignores_role_in_request(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "mallory@example.com", "password": PASSWORD, "role": "ADMIN"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "CUSTOMER"


def test_password_is_stored_hashed(client: TestClient, db_session: Session) -> None:
    register(client)

    user = get_user_by_email(db_session, "alice@example.com")

    assert user is not None
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith("$argon2id$")


def test_email_is_stored_lowercase(client: TestClient) -> None:
    assert register(client, email="Alice@Example.COM")["email"] == "alice@example.com"


def test_duplicate_email_is_rejected_in_any_case(client: TestClient) -> None:
    register(client, email="alice@example.com")

    response = client.post(
        "/auth/register", json={"email": "ALICE@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "A user with this email already exists"


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = client.post("/auth/register", json={"email": "not-an-email", "password": PASSWORD})

    assert response.status_code == 422


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register", json={"email": "alice@example.com", "password": "short"}
    )

    assert response.status_code == 422


# --- Login ---


def test_login_returns_bearer_token(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_email_is_case_insensitive(client: TestClient) -> None:
    register(client)

    assert login(client, email="ALICE@EXAMPLE.COM")


def test_login_with_wrong_password(client: TestClient) -> None:
    register(client)

    response = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_with_unknown_email_gives_same_error(client: TestClient) -> None:
    response = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_requires_form_fields(client: TestClient) -> None:
    assert client.post("/auth/login", data={"username": "alice@example.com"}).status_code == 422


# --- GET /users/me ---


def test_me_returns_logged_in_user(client: TestClient) -> None:
    user = register(client)
    token = login(client)

    response = client.get("/users/me", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == user


def test_me_without_token(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_with_invalid_token(client: TestClient) -> None:
    response = client.get("/users/me", headers=bearer("not.a.token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


def test_me_with_expired_token(client: TestClient) -> None:
    user = register(client)
    expired = create_access_token(user["id"], expires_delta=timedelta(seconds=-1))

    response = client.get("/users/me", headers=bearer(expired))

    assert response.status_code == 401
    assert response.json()["detail"] == "Token has expired"


def test_me_with_token_of_deleted_user(client: TestClient, db_session: Session) -> None:
    user = register(client)
    token = login(client)
    db_session.delete(db_session.get(User, user["id"]))
    db_session.commit()

    response = client.get("/users/me", headers=bearer(token))

    assert response.status_code == 401
