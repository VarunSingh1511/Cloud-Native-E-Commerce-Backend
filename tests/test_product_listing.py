"""Tests for pagination and filtering on GET /products."""

from fastapi.testclient import TestClient

from tests.helpers import create_category, create_product


def names(client: TestClient, url: str) -> list[str]:
    """GET a product list URL and return just the product names."""
    response = client.get(url)
    assert response.status_code == 200, response.text
    return [product["name"] for product in response.json()]


def test_default_page_size_is_20(admin_client: TestClient) -> None:
    for number in range(21):
        create_product(admin_client, name=f"Product {number}")

    assert len(names(admin_client, "/products")) == 20


def test_limit_and_skip_return_the_right_page(admin_client: TestClient) -> None:
    for number in range(1, 6):
        create_product(admin_client, name=f"Product {number}")

    assert names(admin_client, "/products?limit=2") == ["Product 1", "Product 2"]
    assert names(admin_client, "/products?skip=2&limit=2") == ["Product 3", "Product 4"]
    assert names(admin_client, "/products?skip=4&limit=2") == ["Product 5"]
    assert names(admin_client, "/products?skip=10") == []


def test_filter_by_category(admin_client: TestClient) -> None:
    books = create_category(admin_client, "Books")
    toys = create_category(admin_client, "Toys")
    create_product(admin_client, name="Novel", category_id=books["id"])
    create_product(admin_client, name="Robot", category_id=toys["id"])
    create_product(admin_client, name="Uncategorised")

    assert names(admin_client, f"/products?category_id={books['id']}") == ["Novel"]


def test_search_by_name_is_case_insensitive(admin_client: TestClient) -> None:
    create_product(admin_client, name="Gaming Laptop")
    create_product(admin_client, name="Laptop Stand")
    create_product(admin_client, name="Wireless Mouse")

    assert names(admin_client, "/products?q=LAPTOP") == ["Gaming Laptop", "Laptop Stand"]


def test_search_treats_percent_sign_literally(admin_client: TestClient) -> None:
    create_product(admin_client, name="100% Cotton Shirt")
    create_product(admin_client, name="Cotton Socks")

    # Without escaping, "%" would be a SQL wildcard and match every product.
    assert names(admin_client, "/products?q=%25") == ["100% Cotton Shirt"]


def test_filters_combine(admin_client: TestClient) -> None:
    books = create_category(admin_client, "Books")
    create_product(admin_client, name="Python Book", category_id=books["id"])
    create_product(admin_client, name="Java Book", category_id=books["id"])
    create_product(admin_client, name="Python Plush Toy")

    assert names(admin_client, f"/products?category_id={books['id']}&q=python") == ["Python Book"]


def test_invalid_paging_values_are_rejected(admin_client: TestClient) -> None:
    for query in ("limit=0", "limit=101", "skip=-1", "q="):
        assert admin_client.get(f"/products?{query}").status_code == 422, query
