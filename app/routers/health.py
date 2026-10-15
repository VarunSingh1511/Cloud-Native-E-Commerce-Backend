"""Endpoints that report whether the API is running."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/", summary="Check that the API is running")
def read_root() -> dict[str, str]:
    """Provide a lightweight endpoint for confirming the application is online."""
    return {"message": "Cloud E-Commerce API is running"}


@router.get("/health", summary="Health check for Docker and Azure App Service")
def health_check() -> dict[str, str]:
    """Report that the app is up; used by container and cloud health probes."""
    return {"status": "ok", "environment": settings.environment}
