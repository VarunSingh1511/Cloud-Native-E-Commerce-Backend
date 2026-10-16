"""Endpoints about the logged-in user."""

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the logged-in user",
    responses={401: {"description": "Missing, invalid or expired token"}},
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the account that the bearer token belongs to."""
    return current_user
