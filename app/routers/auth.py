"""Registration and login endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse
from app.services import users as user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer account",
    responses={409: {"description": "A user with this email already exists"}},
)
def register(user_data: UserCreate, db: Session = Depends(get_db)) -> User:
    """Register a new user. New accounts always get the CUSTOMER role."""
    return user_service.create_user(db, user_data)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in and get an access token",
    responses={401: {"description": "Incorrect email or password"}},
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """Exchange email and password for a bearer token.

    Uses the standard OAuth2 password form (form fields `username` and `password`,
    where username is the email), which is what Swagger's "Authorize" button sends.
    """
    user = user_service.authenticate(db, form_data.username, form_data.password)
    return Token(access_token=create_access_token(user.id))
