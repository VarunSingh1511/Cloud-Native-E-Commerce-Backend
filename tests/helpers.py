"""Small helpers shared by several test modules."""

from typing import Any

from fastapi.testclient import TestClient

VALID_PRODUCT = {"name": "Mechanical Keyboard", "price": 3000, "description": "RGB keyboard"}
PASSWORD = "s3cure-test-password"


def register(client: TestClient, email: str = "alice@example.com") -> dict[str, Any]:
    """Register a user through the API and return the response body."""
    response = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str = "alice@example.com", password: str = PASSWORD) -> str:
    """Log in through the API and return the access token."""
    # data= sends an HTML form, which is what the OAuth2 login endpoint expects.
    response = client.post("/auth/login", data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    """Build the Authorization header for a token."""
    return {"Authorization": f"Bearer {token}"}


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
