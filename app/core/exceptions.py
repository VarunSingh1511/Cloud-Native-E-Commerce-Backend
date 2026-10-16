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

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """The resource named in the URL does not exist (404)."""

    status_code = 404

    def __init__(self, resource: str) -> None:
        super().__init__(f"{resource} not found")


class ConflictError(AppError):
    """The request clashes with existing data, e.g. a duplicate name (409)."""

    status_code = 409


def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert an AppError into a JSON error response."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
