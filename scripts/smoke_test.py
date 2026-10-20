"""Smoke test for a running deployment of the API.

Usage:
    python scripts/smoke_test.py https://<app-name>.azurewebsites.net
    python scripts/smoke_test.py http://localhost:8000

It sends a few real HTTP requests and prints PASS or FAIL for each check. The exit
code is 0 when everything passed and 1 otherwise, so a CI pipeline can run it
right after a deployment. Only the Python standard library is used, so it runs
anywhere Python is installed.

It registers one throwaway customer with a random email address. No admin
account is needed, and nothing else is changed.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

# The first request after an idle period can be slow (a "cold start" on the free
# App Service tier), so allow up to a minute per request.
TIMEOUT_SECONDS = 60


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Report redirects instead of following them, so they can be checked."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def call(
    method: str,
    url: str,
    json_body: dict[str, Any] | None = None,
    form: dict[str, str] | None = None,
    token: str | None = None,
) -> tuple[int, Any, dict[str, str]]:
    """Send one request and return (status code, parsed body, response headers)."""
    headers = {}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            status, raw, response_headers = response.status, response.read(), response.headers
    except urllib.error.HTTPError as error:  # 4xx, 5xx and (unfollowed) redirects
        status, raw, response_headers = error.code, error.read(), error.headers
    except OSError as error:  # no connection at all: refused, DNS failure, timeout
        return 0, str(error), {}

    try:
        body: Any = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = raw.decode(errors="replace")
    return status, body, dict(response_headers)


def main(base_url: str) -> int:
    base_url = base_url.rstrip("/")
    results: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> bool:
        results.append((name, passed, detail))
        print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
        return passed

    status, body, _ = call("GET", f"{base_url}/health")
    is_ok = status == 200 and isinstance(body, dict) and body.get("status") == "ok"
    check("GET /health is 200 and ok", is_ok, f"{status}")

    status, body, _ = call("GET", f"{base_url}/health/ready")
    check("GET /health/ready reaches the database", status == 200, f"{status} {body}")

    status, _, _ = call("GET", f"{base_url}/docs")
    check("GET /docs (Swagger UI) is 200", status == 200, f"{status}")

    status, body, _ = call("GET", f"{base_url}/products")
    check("GET /products returns a list", status == 200 and isinstance(body, list), f"{status}")

    email = f"smoke-{uuid.uuid4().hex[:12]}@example.com"
    password = uuid.uuid4().hex
    status, body, _ = call(
        "POST", f"{base_url}/auth/register", json_body={"email": email, "password": password}
    )
    check("POST /auth/register creates a customer", status == 201, f"{status}")

    status, body, _ = call(
        "POST", f"{base_url}/auth/login", form={"username": email, "password": password}
    )
    token = body.get("access_token") if status == 200 and isinstance(body, dict) else None
    check("POST /auth/login returns a token", token is not None, f"{status}")

    status, body, _ = call("GET", f"{base_url}/users/me", token=token)
    is_me = (
        status == 200
        and isinstance(body, dict)
        and body.get("email") == email
        and body.get("role") == "CUSTOMER"
    )
    check("GET /users/me returns the new customer", is_me, f"{status}")

    product = {"name": "Smoke test", "price": 1, "description": "Should be rejected"}
    status, _, _ = call("POST", f"{base_url}/products", json_body=product)
    check("Anonymous POST /products is rejected (401)", status == 401, f"{status}")

    status, _, _ = call("POST", f"{base_url}/products", json_body=product, token=token)
    check("Customer POST /products is rejected (403)", status == 403, f"{status}")

    if base_url.startswith("https://"):
        http_url = "http://" + base_url.removeprefix("https://") + "/health"
        status, _, headers = call("GET", http_url)
        location = headers.get("Location", "")
        redirected = status in (301, 302, 307, 308) and location.startswith("https://")
        check("Plain HTTP redirects to HTTPS", redirected, f"{status} -> {location}")

    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/smoke_test.py <base-url>")
    sys.exit(main(sys.argv[1]))
