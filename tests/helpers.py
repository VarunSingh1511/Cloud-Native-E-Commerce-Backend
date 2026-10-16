"""Small helpers shared by several test modules."""

from typing import Any

from fastapi.testclient import TestClient

VALID_PRODUCT = {"name": "Mechanical Keyboard", "price": 3000, "description": "RGB keyboard"}


def create_product(client: TestClient, **overrides: Any) -> dict[str, Any]:
    """Create a product through the API and return the response body."""
    response = client.post("/products", json={**VALID_PRODUCT, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def create_category(client: TestClient, name: str = "Electronics") -> dict[str, Any]:
    """Create a category through the API and return the response body."""
    response = client.post("/categories", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()
