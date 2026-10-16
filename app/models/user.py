"""User accounts. Authentication endpoints that use this table arrive in Week 4."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    """Roles used for authorization (RBAC)."""

    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True adds a unique constraint; index=True speeds up login lookups by email.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Only a password hash is ever stored, never the plain password (Week 4).
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.CUSTOMER
    )
    # server_default: PostgreSQL fills this in, so the time comes from the DB clock.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
