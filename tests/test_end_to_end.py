"""The full shopping journey through the API, as in the Week 5 "done when" goal:

register -> login -> browse -> cart -> checkout -> order, then check the database.
"""

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.order import Order, OrderStatus
from tests.helpers import PASSWORD, bearer


def test_customer_buys_a_product(
    client: TestClient, admin_client: TestClient, db_session: Session
) -> None:
    # The admin sets up the catalog.
    category = admin_client.post("/categories", json={"name": "Laptops"}).json()
    laptop = admin_client.post(
        "/products",
        json={
            "name": "Gaming Laptop",
            "description": "16 GB RAM",
            "price": 75000,
            "category_id": category["id"],
        },
    ).json()
    admin_client.put(f"/inventory/{laptop['id']}", json={"quantity": 3})

    # A new customer registers and logs in.
    credentials = {"email": "eve@example.com", "password": PASSWORD}
    assert client.post("/auth/register", json=credentials).status_code == 201
    login = client.post("/auth/login", data={"username": "eve@example.com", "password": PASSWORD})
    customer = bearer(login.json()["access_token"])

    # They browse the catalog without logging in, filtering by category.
    found = client.get(f"/products?category_id={category['id']}&q=gaming").json()
    assert [product["id"] for product in found] == [laptop["id"]]

    # They add the laptop to their cart and check the total.
    cart = client.post(
        "/cart/items", json={"product_id": laptop["id"], "quantity": 2}, headers=customer
    ).json()
    assert cart["total"] == 150000

    # They place the order.
    checkout = client.post("/orders", headers=customer)
    assert checkout.status_code == 201
    order = checkout.json()
    assert order["status"] == "PLACED"
    assert order["total_amount"] == 150000

    # The order appears in their history, and the cart is now empty.
    history = client.get("/orders", headers=customer).json()
    assert [past_order["id"] for past_order in history] == [order["id"]]
    assert client.get("/cart", headers=customer).json()["items"] == []

    # The database agrees: the order is stored and the stock went down from 3 to 1.
    stored = db_session.get(Order, order["id"])
    assert stored is not None
    assert stored.status == OrderStatus.PLACED
    assert stored.total_amount == Decimal("150000.00")
    stock = db_session.get(Inventory, laptop["id"])
    assert stock is not None
    db_session.refresh(stock)
    assert stock.quantity == 1
