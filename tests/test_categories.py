"""Tests for the category endpoints."""

from fastapi.testclient import TestClient

from tests.helpers import create_category


def test_create_category(admin_client: TestClient) -> None:
    response = admin_client.post("/categories", json={"name": "Electronics"})

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "Electronics"


def test_create_category_strips_whitespace(admin_client: TestClient) -> None:
    assert create_category(admin_client, name="  Books  ")["name"] == "Books"


def test_list_categories_sorted_by_name(admin_client: TestClient) -> None:
    create_category(admin_client, name="Toys")
    create_category(admin_client, name="Books")

    response = admin_client.get("/categories")

    assert response.status_code == 200
    assert [category["name"] for category in response.json()] == ["Books", "Toys"]


def test_get_category(admin_client: TestClient) -> None:
    created = create_category(admin_client)

    response = admin_client.get(f"/categories/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_duplicate_category_name_is_rejected(admin_client: TestClient) -> None:
    create_category(admin_client, name="Electronics")

    response = admin_client.post("/categories", json={"name": "Electronics"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Category 'Electronics' already exists"
    # The failed insert must not break the session: later requests still work.
    assert len(admin_client.get("/categories").json()) == 1


def test_get_nonexistent_category(admin_client: TestClient) -> None:
    response = admin_client.get("/categories/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_create_category_rejects_blank_name(admin_client: TestClient) -> None:
    response = admin_client.post("/categories", json={"name": "   "})

    assert response.status_code == 422


def test_create_category_rejects_too_long_name(admin_client: TestClient) -> None:
    response = admin_client.post("/categories", json={"name": "x" * 101})

    assert response.status_code == 422
