"""Password hashing (Argon2) and login tokens (JWT).

Pure functions with no database or HTTP code, so they are easy to test and reuse.
"""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

# HS256: HMAC with SHA-256. The same SECRET_KEY signs and verifies tokens, which
# fits a single API that both issues and checks them.
ALGORITHM = "HS256"

# Argon2id with the library's recommended defaults. It is deliberately slow and
# memory-hungry, so guessing passwords from a stolen hash is expensive. Each hash
# includes a random salt, so equal passwords produce different hashes.
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an Argon2 hash of the password. The plain password is never stored."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Return True if the password matches the stored hash."""
    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerificationError, InvalidHashError):
        # Wrong password (VerifyMismatchError is a VerificationError) or a malformed hash.
        return False


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT that identifies the user until it expires.

    The token holds only the user ID ("sub"), the issue time ("iat") and the expiry
    ("exp"), not the role: the user is loaded from the database on every request,
    so a role change or deleted account takes effect immediately.
    """
    now = datetime.now(UTC)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """Verify a token's signature and expiry and return the user ID inside it.

    Raises UnauthorizedError for any invalid token. Only HS256 is accepted, which
    blocks tokens that claim a different algorithm (such as "none", unsigned).
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except (jwt.InvalidTokenError, ValueError):
        # Bad signature, malformed token, missing claims, or a non-numeric "sub".
        raise UnauthorizedError()
