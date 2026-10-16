"""Tests for the inventory endpoints."""

from fastapi.testclient import TestClient

from tests.helpers import create_product


def test_new_product_starts_with_zero_stock(admin_client: TestClient) -> None:
    product = create_product(admin_client)

    response = admin_client.get(f"/inventory/{product['id']}")

    assert response.status_code == 200
    assert response.json() == {"product_id": product["id"], "quantity": 0}


def test_set_inventory(admin_client: TestClient) -> None:
    product = create_product(admin_client)

    response = admin_client.put(f"/inventory/{product['id']}", json={"quantity": 25})

    assert response.status_code == 200
    assert response.json() == {"product_id": product["id"], "quantity": 25}
    assert admin_client.get(f"/inventory/{product['id']}").json()["quantity"] == 25


def test_set_inventory_to_zero(admin_client: TestClient) -> None:
    product = create_product(admin_client)
    admin_client.put(f"/inventory/{product['id']}", json={"quantity": 5})

    response = admin_client.put(f"/inventory/{product['id']}", json={"quantity": 0})

    assert response.status_code == 200
    assert response.json()["quantity"] == 0


def test_set_inventory_rejects_negative_quantity(admin_client: TestClient) -> None:
    product = create_product(admin_client)

    response = admin_client.put(f"/inventory/{product['id']}", json={"quantity": -1})

    assert response.status_code == 422
    assert admin_client.get(f"/inventory/{product['id']}").json()["quantity"] == 0


def test_set_inventory_rejects_missing_quantity(admin_client: TestClient) -> None:
    product = create_product(admin_client)

    response = admin_client.put(f"/inventory/{product['id']}", json={})

    assert response.status_code == 422


def test_get_inventory_for_unknown_product(admin_client: TestClient) -> None:
    response = admin_client.get("/inventory/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_set_inventory_for_unknown_product(admin_client: TestClient) -> None:
    response = admin_client.put("/inventory/99999", json={"quantity": 5})

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_deleting_product_removes_its_inventory(admin_client: TestClient) -> None:
    product = create_product(admin_client)
    admin_client.put(f"/inventory/{product['id']}", json={"quantity": 5})

    admin_client.delete(f"/products/{product['id']}")

    assert admin_client.get(f"/inventory/{product['id']}").status_code == 404
