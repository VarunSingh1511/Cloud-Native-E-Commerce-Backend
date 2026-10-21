"""Send requests, errors and logs to Azure Application Insights, when configured.

OpenTelemetry records every HTTP request (path, status code, duration), every
unhandled error with its stack trace, and log records from the app's own loggers.
Microsoft's distro (`azure-monitor-opentelemetry`) sends them to Application
Insights. See docs/monitoring.md.
"""

import logging

from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.core.config import settings


def configure_telemetry(app: FastAPI) -> bool:
    """Start sending telemetry for `app` if APPLICATIONINSIGHTS_CONNECTION_STRING is set.

    Returns whether telemetry was turned on. Tests and local runs leave the
    setting empty, so they send nothing.
    """
    if not settings.applicationinsights_connection_string:
        return False

    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
        # Key authentication is disabled on Application Insights: the app proves
        # who it is with its managed identity (role "Monitoring Metrics Publisher").
        credential=DefaultAzureCredential(),
        # Log records from "app" and its children (app.services.orders, ...)
        # become "traces" in Application Insights.
        logger_name="app",
        enable_live_metrics=True,
        # The automatic FastAPI instrumentation only affects apps created AFTER
        # this call, but ours already exists. It is instrumented explicitly below.
        instrumentation_options={"fastapi": {"enabled": False}},
    )
    # Adds OpenTelemetry middleware to this app: one "request" per HTTP call, and
    # unhandled errors as "exceptions". OTEL_PYTHON_FASTAPI_EXCLUDED_URLS
    # (an App Service setting) leaves out the /health probe.
    FastAPIInstrumentor.instrument_app(app)
    # Python's default level is WARNING; also send the app's INFO records.
    logging.getLogger("app").setLevel(logging.INFO)
    return True
