"""User registration and login."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate

# Used when the email is unknown, so a failed login always runs one (slow) Argon2
# check. Otherwise "unknown email" would answer measurably faster than "wrong
# password", and an attacker could time responses to find registered emails.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return the user with this email (case-insensitive), or None."""
    return db.scalar(select(User).where(User.email == email.lower()))


def create_user(db: Session, user_data: UserCreate, role: UserRole = UserRole.CUSTOMER) -> User:
    """Create a user with a hashed password; raise ConflictError if the email is taken.

    The API always uses the default CUSTOMER role. Only the create_admin command
    passes ADMIN.
    """
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The unique index on users.email rejected the insert.
        db.rollback()
        raise ConflictError("A user with this email already exists")
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Return the user if the email and password match; otherwise raise UnauthorizedError.

    The same message is used for an unknown email and a wrong password, so the
    response does not reveal which emails are registered.
    """
    user = get_user_by_email(db, email)
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise UnauthorizedError("Incorrect email or password")
    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    return user
