"""Tests for the shopping cart endpoints."""

from fastapi.testclient import TestClient

from tests.helpers import VALID_PRODUCT, add_to_cart, create_product, headers_for_new_user


def test_new_user_has_empty_cart(customer_client: TestClient) -> None:
    response = customer_client.get("/cart")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


def test_add_item(customer_client: TestClient, admin_client: TestClient) -> None:
    product = create_product(admin_client, name="Mouse", price=1500)

    response = customer_client.post(
        "/cart/items", json={"product_id": product["id"], "quantity": 2}
    )

    assert response.status_code == 201
    cart = response.json()
    assert cart["total"] == 3000
    [item] = cart["items"]
    assert item["product_id"] == product["id"]
    assert item["product_name"] == "Mouse"
    assert item["unit_price"] == 1500
    assert item["quantity"] == 2
    assert item["line_total"] == 3000


def test_quantity_defaults_to_one(customer_client: TestClient, admin_client: TestClient) -> None:
    product = create_product(admin_client)

    response = customer_client.post("/cart/items", json={"product_id": product["id"]})

    assert response.json()["items"][0]["quantity"] == 1


def test_adding_same_product_again_increases_quantity(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)
    add_to_cart(customer_client, product["id"], quantity=1)

    cart = add_to_cart(customer_client, product["id"], quantity=2)

    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3


def test_total_is_exact_for_decimal_prices(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    pen = create_product(admin_client, name="Pen", price=4.35)

    cart = add_to_cart(customer_client, pen["id"], quantity=100)

    # With floats, 4.35 * 100 is 434.99999999999994; Decimal gives exactly 435.00.
    assert cart["total"] == 435


def test_cart_shows_current_price(customer_client: TestClient, admin_client: TestClient) -> None:
    product = create_product(admin_client, price=100)
    add_to_cart(customer_client, product["id"])

    admin_client.put(f"/products/{product['id']}", json={**VALID_PRODUCT, "price": 80})

    assert customer_client.get("/cart").json()["total"] == 80


def test_add_unknown_product(customer_client: TestClient) -> None:
    response = customer_client.post("/cart/items", json={"product_id": 99999, "quantity": 1})

    assert response.status_code == 400
    assert response.json()["detail"] == "Product 99999 does not exist"


def test_add_rejects_invalid_quantity(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)

    for quantity in (0, -1, 1001):
        response = customer_client.post(
            "/cart/items", json={"product_id": product["id"], "quantity": quantity}
        )
        assert response.status_code == 422, quantity


def test_remove_item(customer_client: TestClient, admin_client: TestClient) -> None:
    product = create_product(admin_client)
    item_id = add_to_cart(customer_client, product["id"])["items"][0]["id"]

    response = customer_client.delete(f"/cart/items/{item_id}")

    assert response.status_code == 204
    assert customer_client.get("/cart").json() == {"items": [], "total": 0}


def test_remove_unknown_item(customer_client: TestClient) -> None:
    response = customer_client.delete("/cart/items/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cart item not found"


def test_cannot_remove_item_from_another_users_cart(
    client: TestClient, customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)
    item_id = add_to_cart(customer_client, product["id"])["items"][0]["id"]
    other_user = headers_for_new_user(client, "bob@example.com")

    response = client.delete(f"/cart/items/{item_id}", headers=other_user)

    assert response.status_code == 404
    assert len(customer_client.get("/cart").json()["items"]) == 1


def test_carts_are_separate_per_user(
    client: TestClient, customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)
    add_to_cart(customer_client, product["id"])
    other_user = headers_for_new_user(client, "bob@example.com")

    assert client.get("/cart", headers=other_user).json()["items"] == []


def test_deleted_product_disappears_from_cart(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = create_product(admin_client)
    add_to_cart(customer_client, product["id"])

    admin_client.delete(f"/products/{product['id']}")

    assert customer_client.get("/cart").json()["items"] == []


def test_cart_requires_login(client: TestClient) -> None:
    assert client.get("/cart").status_code == 401
    assert client.post("/cart/items", json={"product_id": 1}).status_code == 401
    assert client.delete("/cart/items/1").status_code == 401
