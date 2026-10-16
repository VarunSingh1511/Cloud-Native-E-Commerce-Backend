"""Role-based access control: who may call which endpoint."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.helpers import VALID_PRODUCT, create_product

# Every endpoint that changes data. "{id}" is replaced with a real product ID.
WRITE_REQUESTS: list[tuple[str, str, dict[str, Any] | None]] = [
    ("POST", "/products", VALID_PRODUCT),
    ("PUT", "/products/{id}", VALID_PRODUCT),
    ("DELETE", "/products/{id}", None),
    ("POST", "/categories", {"name": "New category"}),
    ("PUT", "/inventory/{id}", {"quantity": 5}),
]

# Readable test names in the pytest output, e.g. "PUT /products/{id}".
WRITE_IDS = [f"{method} {url}" for method, url, _ in WRITE_REQUESTS]


@pytest.mark.parametrize(("method", "url", "body"), WRITE_REQUESTS, ids=WRITE_IDS)
def test_anonymous_user_cannot_write(
    client: TestClient,
    admin_client: TestClient,
    method: str,
    url: str,
    body: dict[str, Any] | None,
) -> None:
    product = create_product(admin_client)

    response = client.request(method, url.format(id=product["id"]), json=body)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(("method", "url", "body"), WRITE_REQUESTS, ids=WRITE_IDS)
def test_customer_cannot_write(
    customer_client: TestClient,
    admin_client: TestClient,
    method: str,
    url: str,
    body: dict[str, Any] | None,
) -> None:
    product = create_product(admin_client)

    response = customer_client.request(method, url.format(id=product["id"]), json=body)

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_forbidden_request_changes_nothing(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)

    customer_client.delete(f"/products/{product['id']}")

    assert admin_client.get(f"/products/{product['id']}").status_code == 200


def test_reads_are_public(client: TestClient, admin_client: TestClient) -> None:
    product_id = create_product(admin_client)["id"]

    for url in ("/products", f"/products/{product_id}", "/categories", f"/inventory/{product_id}"):
        assert client.get(url).status_code == 200, url


def test_customer_can_read(customer_client: TestClient, admin_client: TestClient) -> None:
    product = create_product(admin_client)

    assert customer_client.get(f"/products/{product['id']}").status_code == 200
