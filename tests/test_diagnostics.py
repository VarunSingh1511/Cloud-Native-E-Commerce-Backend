"""Tests for POST /diagnostics/error, the deliberate error for the monitoring demo."""

from fastapi.testclient import TestClient

from app.main import app


def test_anonymous_cannot_trigger_sample_error(client: TestClient) -> None:
    assert client.post("/diagnostics/error").status_code == 401


def test_customer_cannot_trigger_sample_error(customer_client: TestClient) -> None:
    assert customer_client.post("/diagnostics/error").status_code == 403


def test_admin_gets_http_500(admin_client: TestClient) -> None:
    # A normal TestClient re-raises server errors inside the test. This one
    # returns the response a real caller would get instead.
    with TestClient(app, raise_server_exceptions=False, headers=admin_client.headers) as caller:
        response = caller.post("/diagnostics/error")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"  # no stack trace leaks to the caller
