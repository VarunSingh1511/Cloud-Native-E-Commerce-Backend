"""Tests for viewing orders: customers see only their own, admins see all."""

from fastapi.testclient import TestClient

from tests.helpers import headers_for_new_user, place_order, stocked_product


def test_new_user_has_no_orders(customer_client: TestClient) -> None:
    response = customer_client.get("/orders")

    assert response.status_code == 200
    assert response.json() == []


def test_list_my_orders_newest_first(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client)
    first = place_order(customer_client, product["id"])
    second = place_order(customer_client, product["id"])

    orders = customer_client.get("/orders").json()

    assert [order["id"] for order in orders] == [second["id"], first["id"]]
    assert orders[0]["items"][0]["product_id"] == product["id"]


def test_get_my_order(customer_client: TestClient, admin_client: TestClient) -> None:
    order = place_order(customer_client, stocked_product(admin_client)["id"])

    response = customer_client.get(f"/orders/{order['id']}")

    assert response.status_code == 200
    assert response.json() == order


def test_get_unknown_order(customer_client: TestClient) -> None:
    response = customer_client.get("/orders/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_customer_cannot_see_another_customers_orders(
    client: TestClient, customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client)
    my_order = place_order(customer_client, product["id"])
    bob = headers_for_new_user(client, "bob@example.com")

    assert client.get("/orders", headers=bob).json() == []
    # 404, not 403: Bob cannot even tell that this order exists.
    response = client.get(f"/orders/{my_order['id']}", headers=bob)
    assert response.status_code == 404


def test_admin_sees_all_orders(
    client: TestClient, customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client)
    alice_order = place_order(customer_client, product["id"])
    bob = headers_for_new_user(client, "bob@example.com")
    client.post("/cart/items", json={"product_id": product["id"]}, headers=bob)
    bob_order = client.post("/orders", headers=bob).json()

    orders = admin_client.get("/orders").json()

    assert {order["id"] for order in orders} == {alice_order["id"], bob_order["id"]}
    assert admin_client.get(f"/orders/{bob_order['id']}").status_code == 200


def test_orders_require_login(client: TestClient) -> None:
    assert client.get("/orders").status_code == 401
    assert client.get("/orders/1").status_code == 401
