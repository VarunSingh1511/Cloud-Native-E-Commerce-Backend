"""Tests for the product endpoints."""

from fastapi.testclient import TestClient

VALID_PRODUCT = {"name": "Mechanical Keyboard", "price": 3000, "description": "RGB keyboard"}


# --- Success cases ---


def test_get_all_products(client: TestClient) -> None:
    response = client.get("/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2


def test_get_existing_product(client: TestClient) -> None:
    response = client.get("/products/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_create_product(client: TestClient) -> None:
    response = client.post("/products", json=VALID_PRODUCT)

    assert response.status_code == 201
    assert response.json() == {"id": 3, **VALID_PRODUCT}


def test_update_product(client: TestClient) -> None:
    payload = {"name": "Updated Laptop", "price": 80000, "description": "Updated description"}

    response = client.put("/products/1", json=payload)

    assert response.status_code == 200
    assert response.json() == {"id": 1, **payload}


def test_delete_product(client: TestClient) -> None:
    response = client.delete("/products/1")

    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted successfully"}
    assert client.get("/products/1").status_code == 404


# --- 404: product does not exist ---


def test_get_nonexistent_product(client: TestClient) -> None:
    response = client.get("/products/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_nonexistent_product(client: TestClient) -> None:
    response = client.put("/products/99999", json=VALID_PRODUCT)

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_delete_nonexistent_product(client: TestClient) -> None:
    response = client.delete("/products/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


# --- 422: request fails validation ---


def test_create_rejects_invalid_values(client: TestClient) -> None:
    response = client.post("/products", json={"name": "", "price": 0, "description": ""})

    assert response.status_code == 422


def test_create_rejects_missing_field(client: TestClient) -> None:
    response = client.post("/products", json={"name": "Keyboard", "price": 3000})

    assert response.status_code == 422


def test_update_rejects_negative_price(client: TestClient) -> None:
    response = client.put("/products/1", json={**VALID_PRODUCT, "price": -5})

    assert response.status_code == 422
    # A rejected update must not change the stored product.
    assert client.get("/products/1").json()["name"] == "Laptop"


def test_non_integer_product_id_is_rejected(client: TestClient) -> None:
    response = client.get("/products/abc")

    assert response.status_code == 422
