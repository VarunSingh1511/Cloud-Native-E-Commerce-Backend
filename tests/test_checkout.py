"""Tests for checkout (POST /orders): the single-transaction order process."""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.services import orders as order_service
from app.services.users import get_user_by_email
from tests.helpers import VALID_PRODUCT, add_to_cart, stocked_product


def stock_of(client: TestClient, product_id: int) -> int:
    return client.get(f"/inventory/{product_id}").json()["quantity"]


def order_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Order))


# --- Success ---


def test_checkout_creates_order(customer_client: TestClient, admin_client: TestClient) -> None:
    laptop = stocked_product(admin_client, stock=5, name="Laptop", price=100)
    pen = stocked_product(admin_client, stock=10, name="Pen", price=19.99)
    add_to_cart(customer_client, laptop["id"], quantity=2)
    add_to_cart(customer_client, pen["id"], quantity=3)

    response = customer_client.post("/orders")

    assert response.status_code == 201
    order = response.json()
    assert order["status"] == "PLACED"
    assert order["total_amount"] == 259.97  # 2 x 100 + 3 x 19.99
    assert [
        (line["product_name"], line["unit_price"], line["quantity"], line["line_total"])
        for line in order["items"]
    ] == [("Laptop", 100, 2, 200), ("Pen", 19.99, 3, 59.97)]


def test_checkout_logs_the_order_without_personal_data(
    customer_client: TestClient, admin_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    product = stocked_product(admin_client, stock=5, price=100)
    add_to_cart(customer_client, product["id"], quantity=2)
    caplog.set_level(logging.INFO, logger="app.services.orders")

    order = customer_client.post("/orders").json()

    assert f"Order {order['id']} placed by user" in caplog.text
    assert "total 200.00" in caplog.text
    assert "customer@example.com" not in caplog.text


def test_checkout_takes_stock_and_empties_cart(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client, stock=5)
    add_to_cart(customer_client, product["id"], quantity=2)

    customer_client.post("/orders")

    assert stock_of(customer_client, product["id"]) == 3
    assert customer_client.get("/cart").json()["items"] == []


def test_checkout_can_buy_the_last_units(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client, stock=2)
    add_to_cart(customer_client, product["id"], quantity=2)

    assert customer_client.post("/orders").status_code == 201
    assert stock_of(customer_client, product["id"]) == 0


def test_order_keeps_price_paid_after_price_change(
    customer_client: TestClient, admin_client: TestClient, db_session: Session
) -> None:
    product = stocked_product(admin_client, price=100)
    add_to_cart(customer_client, product["id"])
    order_id = customer_client.post("/orders").json()["id"]

    admin_client.put(f"/products/{product['id']}", json={**VALID_PRODUCT, "price": 999})

    order = db_session.get(Order, order_id)
    assert order is not None
    db_session.refresh(order)
    assert order.total_amount == 100
    assert order.items[0].unit_price == 100


def test_deleting_ordered_product_keeps_order_history(
    customer_client: TestClient, admin_client: TestClient, db_session: Session
) -> None:
    product = stocked_product(admin_client, name="Discontinued Lamp")
    add_to_cart(customer_client, product["id"])
    order_id = customer_client.post("/orders").json()["id"]

    assert admin_client.delete(f"/products/{product['id']}").status_code == 200

    [line] = db_session.scalars(select(OrderItem).where(OrderItem.order_id == order_id))
    db_session.refresh(line)
    assert line.product_id is None
    assert line.product_name == "Discontinued Lamp"


# --- Failures leave everything unchanged ---


def test_empty_cart_cannot_be_ordered(customer_client: TestClient, db_session: Session) -> None:
    response = customer_client.post("/orders")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"
    assert order_count(db_session) == 0


def test_insufficient_stock_changes_nothing(
    customer_client: TestClient, admin_client: TestClient, db_session: Session
) -> None:
    plenty = stocked_product(admin_client, stock=10, name="Plenty")
    scarce = stocked_product(admin_client, stock=1, name="Scarce")
    add_to_cart(customer_client, plenty["id"], quantity=2)
    add_to_cart(customer_client, scarce["id"], quantity=3)

    response = customer_client.post("/orders")

    assert response.status_code == 409
    assert response.json()["detail"] == "Not enough stock for 'Scarce' (requested 3, available 1)"
    assert order_count(db_session) == 0
    assert stock_of(customer_client, plenty["id"]) == 10  # not taken either
    assert stock_of(customer_client, scarce["id"]) == 1
    assert len(customer_client.get("/cart").json()["items"]) == 2


def test_out_of_stock_product_cannot_be_ordered(
    customer_client: TestClient, admin_client: TestClient
) -> None:
    product = stocked_product(admin_client, stock=0, name="Sold Out")
    add_to_cart(customer_client, product["id"])

    assert customer_client.post("/orders").status_code == 409


def test_failure_mid_checkout_rolls_back_everything(
    monkeypatch: pytest.MonkeyPatch,
    customer_client: TestClient,
    admin_client: TestClient,
    db_session: Session,
) -> None:
    """Simulate a crash after the order rows were written but before the commit."""
    product = stocked_product(admin_client, stock=5)
    add_to_cart(customer_client, product["id"], quantity=2)
    customer = get_user_by_email(db_session, "customer@example.com")
    assert customer is not None

    def crash(*args: object) -> None:
        # By now the order and its items have been INSERTed (flushed), not committed.
        assert order_count(db_session) == 1
        raise RuntimeError("simulated failure while reducing stock")

    monkeypatch.setattr(order_service, "_reduce_stock", crash)

    with pytest.raises(RuntimeError):
        order_service.checkout(db_session, customer)

    # The rollback removed the half-finished order; stock and cart are untouched.
    assert order_count(db_session) == 0
    assert stock_of(customer_client, product["id"]) == 5
    assert customer_client.get("/cart").json()["items"][0]["quantity"] == 2


def test_checkout_requires_login(client: TestClient) -> None:
    assert client.post("/orders").status_code == 401
