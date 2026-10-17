"""Tests for admin order status changes (PATCH /orders/{id}/status)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.helpers import add_to_cart, place_order, stocked_product

# The steps needed to bring a new (PLACED) order into each status.
PATH_TO_STATUS = {
    "PLACED": [],
    "SHIPPED": ["SHIPPED"],
    "DELIVERED": ["SHIPPED", "DELIVERED"],
    "CANCELLED": ["CANCELLED"],
}

BLOCKED_CHANGES = [
    ("PLACED", "PLACED"),
    ("PLACED", "DELIVERED"),
    ("SHIPPED", "PLACED"),
    ("SHIPPED", "CANCELLED"),
    ("DELIVERED", "SHIPPED"),
    ("DELIVERED", "CANCELLED"),
    ("CANCELLED", "PLACED"),
    ("CANCELLED", "SHIPPED"),
]
BLOCKED_IDS = [f"{current}->{new}" for current, new in BLOCKED_CHANGES]


def set_status(admin_client: TestClient, order_id: int, status: str) -> Any:
    return admin_client.patch(f"/orders/{order_id}/status", json={"status": status})


def order_in_status(
    customer_client: TestClient, admin_client: TestClient, status: str
) -> dict[str, Any]:
    """Place an order and move it to the given status."""
    order = place_order(customer_client, stocked_product(admin_client)["id"])
    for step in PATH_TO_STATUS[status]:
        assert set_status(admin_client, order["id"], step).status_code == 200
    return order


def stock_of(client: TestClient, product_id: int) -> int:
    return client.get(f"/inventory/{product_id}").json()["quantity"]


def test_ship_then_deliver(customer_client: TestClient, admin_client: TestClient) -> None:
    order = place_order(customer_client, stocked_product(admin_client)["id"])

    shipped = set_status(admin_client, order["id"], "SHIPPED")
    delivered = set_status(admin_client, order["id"], "DELIVERED")

    assert shipped.status_code == 200
    assert shipped.json()["status"] == "SHIPPED"
    assert delivered.json()["status"] == "DELIVERED"
    # The customer sees the new status too.
    assert customer_client.get(f"/orders/{order['id']}").json()["status"] == "DELIVERED"


@pytest.mark.parametrize(("current", "new"), BLOCKED_CHANGES, ids=BLOCKED_IDS)
def test_blocked_status_changes(
    customer_client: TestClient, admin_client: TestClient, current: str, new: str
) -> None:
    order = order_in_status(customer_client, admin_client, current)

    response = set_status(admin_client, order["id"], new)

    assert response.status_code == 409
    assert response.json()["detail"] == f"Cannot change order status from {current} to {new}"


def test_cancel_returns_stock(customer_client: TestClient, admin_client: TestClient) -> None:
    product = stocked_product(admin_client, stock=5)
    order = place_order(customer_client, product["id"], quantity=3)
    assert stock_of(admin_client, product["id"]) == 2

    response = set_status(admin_client, order["id"], "CANCELLED")

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    assert stock_of(admin_client, product["id"]) == 5


def test_cancelling_twice_does_not_restock_twice(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client, stock=5)
    order = place_order(customer_client, product["id"], quantity=3)
    set_status(admin_client, order["id"], "CANCELLED")

    assert set_status(admin_client, order["id"], "CANCELLED").status_code == 409
    assert stock_of(admin_client, product["id"]) == 5


def test_cancel_with_deleted_product_restocks_the_rest(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    kept = stocked_product(admin_client, stock=5, name="Kept")
    removed = stocked_product(admin_client, stock=5, name="Removed")
    add_to_cart(customer_client, kept["id"], quantity=2)
    add_to_cart(customer_client, removed["id"], quantity=2)
    order = customer_client.post("/orders").json()
    admin_client.delete(f"/products/{removed['id']}")

    response = set_status(admin_client, order["id"], "CANCELLED")

    assert response.status_code == 200
    assert stock_of(admin_client, kept["id"]) == 5


def test_unknown_status_value_is_rejected(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    order = place_order(customer_client, stocked_product(admin_client)["id"])

    assert set_status(admin_client, order["id"], "LOST").status_code == 422


def test_unknown_order(admin_client: TestClient) -> None:
    response = set_status(admin_client, 99999, "SHIPPED")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_only_admins_can_change_status(
    client: TestClient, customer_client: TestClient, admin_client: TestClient
) -> None:
    order = place_order(customer_client, stocked_product(admin_client)["id"])

    assert set_status(customer_client, order["id"], "CANCELLED").status_code == 403
    assert set_status(client, order["id"], "CANCELLED").status_code == 401
    assert customer_client.get(f"/orders/{order['id']}").json()["status"] == "PLACED"
