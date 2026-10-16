"""Tests for the category endpoints."""

from fastapi.testclient import TestClient

from tests.helpers import create_category


def test_create_category(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "Electronics"})

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "Electronics"


def test_create_category_strips_whitespace(client: TestClient) -> None:
    assert create_category(client, name="  Books  ")["name"] == "Books"


def test_list_categories_sorted_by_name(client: TestClient) -> None:
    create_category(client, name="Toys")
    create_category(client, name="Books")

    response = client.get("/categories")

    assert response.status_code == 200
    assert [category["name"] for category in response.json()] == ["Books", "Toys"]


def test_get_category(client: TestClient) -> None:
    created = create_category(client)

    response = client.get(f"/categories/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_duplicate_category_name_is_rejected(client: TestClient) -> None:
    create_category(client, name="Electronics")

    response = client.post("/categories", json={"name": "Electronics"})

    assert response.status_code == 409
    assert response.json()["detail"] == "Category 'Electronics' already exists"
    # The failed insert must not break the session: later requests still work.
    assert len(client.get("/categories").json()) == 1


def test_get_nonexistent_category(client: TestClient) -> None:
    response = client.get("/categories/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


def test_create_category_rejects_blank_name(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "   "})

    assert response.status_code == 422


def test_create_category_rejects_too_long_name(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "x" * 101})

    assert response.status_code == 422
