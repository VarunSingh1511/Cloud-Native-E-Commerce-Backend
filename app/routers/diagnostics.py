"""An admin-only endpoint that fails on purpose, to demonstrate error monitoring."""

from fastapi import APIRouter, Depends

from app.core.dependencies import ADMIN_ONLY_RESPONSES, require_admin

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


class SampleError(RuntimeError):
    """The deliberate error raised by POST /diagnostics/error."""


@router.post(
    "/error",
    summary="Fail on purpose (monitoring demo)",
    responses={500: {"description": "Always: the deliberate sample error"}, **ADMIN_ONLY_RESPONSES},
    dependencies=[Depends(require_admin)],
)
def raise_sample_error() -> None:
    """Raise an unhandled error, so the request fails with HTTP 500.

    Nothing catches it, exactly like a real bug. It then shows up in Application
    Insights (Failures, with the stack trace), in the App Service console logs, and
    triggers the HTTP 5xx email alert. Admin-only, so nobody else can trigger alerts.
    """
    raise SampleError("Sample error for the monitoring demo")
