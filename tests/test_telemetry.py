"""Tests for app/core/telemetry.py. Azure is never contacted: the call is replaced."""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI

from app.core import telemetry
from app.core.config import settings


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Record calls to configure_azure_monitor instead of starting real telemetry."""
    recorded: list[dict[str, Any]] = []
    monkeypatch.setattr(telemetry, "configure_azure_monitor", lambda **kw: recorded.append(kw))
    app_logger = logging.getLogger("app")
    original_level = app_logger.level
    yield recorded
    app_logger.setLevel(original_level)


def has_opentelemetry_middleware(app: FastAPI) -> bool:
    return any("OpenTelemetry" in str(middleware.cls) for middleware in app.user_middleware)


def test_telemetry_is_off_without_connection_string(
    monkeypatch: pytest.MonkeyPatch, calls: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(settings, "applicationinsights_connection_string", None)
    app = FastAPI()

    assert telemetry.configure_telemetry(app) is False
    assert calls == []
    assert not has_opentelemetry_middleware(app)


def test_telemetry_uses_connection_string_and_azure_identity(
    monkeypatch: pytest.MonkeyPatch, calls: list[dict[str, Any]]
) -> None:
    monkeypatch.setattr(
        settings, "applicationinsights_connection_string", "InstrumentationKey=00000000-test"
    )

    assert telemetry.configure_telemetry(FastAPI()) is True
    assert len(calls) == 1
    call = calls[0]
    assert call["connection_string"] == "InstrumentationKey=00000000-test"
    # Key authentication is disabled in Azure, so an identity must be passed.
    assert isinstance(call["credential"], DefaultAzureCredential)
    assert call["logger_name"] == "app"
    assert logging.getLogger("app").level == logging.INFO


def test_telemetry_instruments_the_existing_app(
    monkeypatch: pytest.MonkeyPatch, calls: list[dict[str, Any]]
) -> None:
    # Regression test: the first version relied on the library's automatic
    # instrumentation, which only affects apps created later, so no request
    # reached Application Insights.
    monkeypatch.setattr(
        settings, "applicationinsights_connection_string", "InstrumentationKey=00000000-test"
    )
    app = FastAPI()

    telemetry.configure_telemetry(app)

    assert has_opentelemetry_middleware(app)
