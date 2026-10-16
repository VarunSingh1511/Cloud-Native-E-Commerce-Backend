"""Tests for password hashing and JWT helpers (no HTTP involved)."""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

PASSWORD = "correct horse battery staple"


# --- Password hashing ---


def test_hash_is_not_the_password_and_verifies() -> None:
    hashed = hash_password(PASSWORD)

    assert hashed != PASSWORD
    assert hashed.startswith("$argon2id$")
    assert verify_password(PASSWORD, hashed)


def test_wrong_password_does_not_verify() -> None:
    assert not verify_password("wrong password", hash_password(PASSWORD))


def test_same_password_hashes_differently_each_time() -> None:
    # A random salt per hash means equal passwords cannot be spotted in the DB.
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_malformed_hash_does_not_verify() -> None:
    assert not verify_password(PASSWORD, "not-a-real-hash")


# --- Tokens ---


def test_token_round_trip() -> None:
    token = create_access_token(42)

    assert decode_access_token(token) == 42


def test_expired_token_is_rejected() -> None:
    token = create_access_token(42, expires_delta=timedelta(seconds=-1))

    with pytest.raises(UnauthorizedError, match="Token has expired"):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "an-attackers-guess-at-the-secret-key-123456",
        algorithm="HS256",
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(forged)


def test_token_with_edited_payload_is_rejected() -> None:
    header, _, signature = create_access_token(42).split(".")
    # Swap in a payload claiming to be user 1, but keep the original signature.
    forged_payload = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.secret_key.get_secret_value(),
        algorithm="HS256",
    ).split(".")[1]

    with pytest.raises(UnauthorizedError):
        decode_access_token(f"{header}.{forged_payload}.{signature}")


def test_unsigned_none_algorithm_token_is_rejected() -> None:
    unsigned = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) + timedelta(minutes=5)}, key=None, algorithm="none"
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(unsigned)


def test_token_without_expiry_is_rejected() -> None:
    no_expiry = jwt.encode(
        {"sub": "42"}, settings.secret_key.get_secret_value(), algorithm="HS256"
    )

    with pytest.raises(UnauthorizedError):
        decode_access_token(no_expiry)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(UnauthorizedError):
        decode_access_token("not.a.token")
