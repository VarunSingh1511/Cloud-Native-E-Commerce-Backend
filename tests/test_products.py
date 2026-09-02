"""Tests for Week 1 product endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.products import reset_products

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_sample_products() -> None:
    """Ensure each test starts with the same in-memory sample data."""
    reset_products()


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Cloud E-Commerce API is running"}


def test_get_all_products() -> None:
    response = client.get("/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 2


def test_get_existing_product() -> None:
    response = client.get("/products/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_get_nonexistent_product() -> None:
    response = client.get("/products/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_create_product() -> None:
    payload = {"name": "Mechanical Keyboard", "price": 3000, "description": "RGB keyboard"}

    response = client.post("/products", json=payload)

    assert response.status_code == 201
    assert response.json() == {"id": 3, **payload}


def test_update_product() -> None:
    payload = {"name": "Updated Laptop", "price": 80000, "description": "Updated description"}

    response = client.put("/products/1", json=payload)

    assert response.status_code == 200
    assert response.json() == {"id": 1, **payload}


def test_delete_product() -> None:
    response = client.delete("/products/1")

    assert response.status_code == 200
    assert response.json() == {"message": "Product deleted successfully"}
    assert client.get("/products/1").status_code == 404


def test_invalid_product_is_rejected() -> None:
    response = client.post(
        "/products",
        json={"name": "", "price": 0, "description": ""},
    )

    assert response.status_code == 422
