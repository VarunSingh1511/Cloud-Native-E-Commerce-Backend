"""Application errors raised by services and turned into HTTP responses.

Services raise these instead of FastAPI's HTTPException, so business logic does
not depend on HTTP. One exception handler (registered in main.py) converts any
AppError into a JSON response with the same shape FastAPI uses: {"detail": "..."}.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for expected errors; subclasses choose the HTTP status code."""

    status_code: int = 500
    # Extra HTTP response headers, if a subclass needs any.
    headers: dict[str, str] | None = None

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """The resource named in the URL does not exist (404)."""

    status_code = 404

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class BadRequestError(AppError):
    """The request body is well-formed but refers to something invalid (400)."""

    status_code = 400


class UnauthorizedError(AppError):
    """Not logged in: the token is missing, invalid or expired (401).

    "Unauthorized" is HTTP's historical name; it really means "unauthenticated".
    """

    status_code = 401
    # Required by the HTTP spec for 401: tells the client which login scheme to use.
    headers = {"WWW-Authenticate": "Bearer"}

    def __init__(self, message: str = "Could not validate credentials") -> None:
        super().__init__(message)


class ForbiddenError(AppError):
    """Logged in, but not allowed to do this, e.g. a customer calling an admin endpoint (403)."""

    status_code = 403


class ConflictError(AppError):
    """The request clashes with existing data, e.g. a duplicate name (409)."""

    status_code = 409


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert an AppError into a JSON error response."""
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message}, headers=exc.headers
    )
