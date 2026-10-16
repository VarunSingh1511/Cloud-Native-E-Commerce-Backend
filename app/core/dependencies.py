"""FastAPI dependencies for authentication (who are you?) and authorization (may you?)."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# Reads the token from the "Authorization: Bearer <token>" header. If the header
# is missing it returns 401 by itself. tokenUrl tells Swagger's "Authorize"
# button where to log in.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Swagger documentation for endpoints protected by require_admin.
ADMIN_ONLY_RESPONSES = {
    401: {"description": "Not logged in, or the token is invalid or expired"},
    403: {"description": "Admin access required"},
}


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Return the logged-in user, or raise 401.

    The user is loaded from the database on every request, so a deleted account
    stops working immediately even if its token has not expired yet.
    """
    user_id = decode_access_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError()
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Allow only ADMIN users: 401 if not logged in, 403 if logged in as a customer."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError("Admin access required")
    return current_user
