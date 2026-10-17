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


def set_stock(admin_client: TestClient, product_id: int, quantity: int) -> None:
    """Set a product's stock level (admin only)."""
    response = admin_client.put(f"/inventory/{product_id}", json={"quantity": quantity})
    assert response.status_code == 200, response.text


def stocked_product(admin_client: TestClient, stock: int = 10, **overrides: Any) -> dict[str, Any]:
    """Create a product and give it some stock; return the product."""
    product = create_product(admin_client, **overrides)
    set_stock(admin_client, product["id"], stock)
    return product


def add_to_cart(client: TestClient, product_id: int, quantity: int = 1) -> dict[str, Any]:
    """Add a product to the logged-in user's cart and return the cart."""
    response = client.post("/cart/items", json={"product_id": product_id, "quantity": quantity})
    assert response.status_code == 201, response.text
    return response.json()


def place_order(client: TestClient, product_id: int, quantity: int = 1) -> dict[str, Any]:
    """Put one product in the cart and check out; return the new order."""
    add_to_cart(client, product_id, quantity)
    response = client.post("/orders")
    assert response.status_code == 201, response.text
    return response.json()


def headers_for_new_user(client: TestClient, email: str) -> dict[str, str]:
    """Register and log in another user; return headers that act as that user."""
    register(client, email=email)
    return bearer(login(client, email=email))


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
