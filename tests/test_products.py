"""Tests for the product endpoints, running against the test database."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import Product
from tests.helpers import VALID_PRODUCT, create_category, create_product


# --- Success cases ---


def test_list_is_empty_on_fresh_database(client: TestClient) -> None:
    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == []


def test_get_all_products(client: TestClient) -> None:
    create_product(client, name="Laptop")
    create_product(client, name="Wireless Mouse")

    response = client.get("/products")

    assert response.status_code == 200
    assert [product["name"] for product in response.json()] == ["Laptop", "Wireless Mouse"]


def test_get_existing_product(client: TestClient) -> None:
    created = create_product(client)

    response = client.get(f"/products/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_create_product(client: TestClient) -> None:
    response = client.post("/products", json=VALID_PRODUCT)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body == {"id": body["id"], "category_id": None, **VALID_PRODUCT}


def test_created_product_is_saved_in_database(client: TestClient, db_session: Session) -> None:
    created = create_product(client)

    product = db_session.get(Product, created["id"])

    assert product is not None
    assert product.name == VALID_PRODUCT["name"]


def test_price_keeps_two_decimal_places(client: TestClient) -> None:
    created = create_product(client, price=19.99)

    assert client.get(f"/products/{created['id']}").json()["price"] == 19.99


def test_update_product(client: TestClient) -> None:
    created = create_product(client)
    payload = {"name": "Updated Laptop", "price": 80000, "description": "Updated description"}

    response = client.put(f"/products/{created['id']}", json=payload)

    assert response.status_code == 200
    assert response.json() == {"id": created["id"], "category_id": None, **payload}


# --- Products and categories ---


def test_create_product_in_category(client: TestClient) -> None:
    category = create_category(client)

    created = create_product(client, category_id=category["id"])

    assert created["category_id"] == category["id"]


def test_update_moves_product_to_another_category(client: TestClient) -> None:
    created = create_product(client, category_id=create_category(client, "Books")["id"])
    toys = create_category(client, "Toys")

    response = client.put(
        f"/products/{created['id']}", json={**VALID_PRODUCT, "category_id": toys["id"]}
    )

    assert response.status_code == 200
    assert response.json()["category_id"] == toys["id"]


def test_create_rejects_unknown_category(client: TestClient) -> None:
    response = client.post("/products", json={**VALID_PRODUCT, "category_id": 99999})

    assert response.status_code == 400
    assert response.json()["detail"] == "Category 99999 does not exist"


def test_update_rejects_unknown_category(client: TestClient) -> None:
    created = create_product(client)

    response = client.put(
        f"/products/{created['id']}", json={**VALID_PRODUCT, "category_id": 99999}
    )

    assert response.status_code == 400
    # The rejected update must not change the stored product.
    assert client.get(f"/products/{created['id']}").json()["category_id"] is None


def test_delete_product(client: TestClient) -> None:
    created = create_product(client)

    response = client.delete(f"/products/{created['id']}")

    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted successfully"}
    assert client.get(f"/products/{created['id']}").status_code == 404


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
    created = create_product(client)

    response = client.put(f"/products/{created['id']}", json={**VALID_PRODUCT, "price": -5})

    assert response.status_code == 422
    # A rejected update must not change the stored product.
    assert client.get(f"/products/{created['id']}").json()["price"] == VALID_PRODUCT["price"]


def test_non_integer_product_id_is_rejected(client: TestClient) -> None:
    response = client.get("/products/abc")

    assert response.status_code == 422


def test_create_rejects_price_above_database_limit(client: TestClient) -> None:
    response = client.post("/products", json={**VALID_PRODUCT, "price": 100_000_000})

    assert response.status_code == 422
