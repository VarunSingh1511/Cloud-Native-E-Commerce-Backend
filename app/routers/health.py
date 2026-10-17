"""Endpoints that report whether the API is running and able to serve requests."""

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get("/", summary="Check that the API is running")
def read_root() -> dict[str, str]:
    """Provide a lightweight endpoint for confirming the application is online."""
    return {"message": "Cloud E-Commerce API is running"}


@router.get("/health", summary="Liveness: is the process running?")
def health_check() -> dict[str, str]:
    """Report that the app process is up. Does not touch the database.

    A liveness check should only fail if the process itself is broken (then
    restarting it helps). A database outage is not fixed by restarting the API.
    """
    return {"status": "ok", "environment": settings.environment}


@router.get(
    "/health/ready",
    summary="Readiness: can the API reach the database?",
    responses={503: {"description": "The database is unreachable"}},
)
def readiness_check(response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    """Run a trivial query; return 503 if the database cannot be reached.

    Docker Compose uses this to report the API as healthy only when it can
    actually serve requests. Monitoring can alert on it later.
    """
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "database": "unreachable"}
    return {"status": "ok", "database": "ok"}
