"""Request and response schemas for users and login tokens."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Registration data. There is deliberately no `role` field: everyone who
    registers becomes a CUSTOMER, so nobody can make themselves an admin."""

    # EmailStr rejects malformed addresses (uses the email-validator library).
    email: EmailStr
    # max_length stops someone sending megabytes to the (deliberately slow) hasher.
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, email: str) -> str:
        """Store emails in lowercase so Alice@x.com and alice@x.com are one account."""
        return email.lower()


class UserResponse(BaseModel):
    """User data returned by the API. Never includes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    """Login response, in the format OAuth2 clients (and Swagger) expect."""

    access_token: str
    token_type: str = "bearer"
