"""Two customers buy the last unit at the same moment, in real concurrent transactions.

The other tests share one rolled-back connection, which cannot show row locking. Here
each buyer has its own session (its own connection) and really commits, so the
database's locks decide the outcome. The test deletes everything it created.
"""

import threading
import uuid
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select

from app.core.exceptions import ConflictError
from app.db.session import SessionLocal
from app.models.cart import Cart, CartItem
from app.models.inventory import Inventory
from app.models.order import Order
from app.models.product import Product
from app.models.user import User, UserRole
from app.services import orders as order_service

BUYERS = 2


@pytest.fixture
def last_unit() -> Iterator[tuple[int, list[int]]]:
    """Commit a product with 1 unit in stock and two customers who each have it in their cart."""
    with SessionLocal() as db:
        product = Product(name="Last unit", description="Only one left", price=Decimal("100.00"))
        db.add(product)
        db.flush()
        db.add(Inventory(product_id=product.id, quantity=1))
        user_ids = []
        for _ in range(BUYERS):
            # The password hash is never checked here: checkout gets the user directly.
            user = User(email=f"race-{uuid.uuid4().hex}@example.com", hashed_password="unused",
                        role=UserRole.CUSTOMER)
            db.add(user)
            db.flush()
            cart = Cart(user_id=user.id)
            db.add(cart)
            db.flush()
            db.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
            user_ids.append(user.id)
        db.commit()
        product_id = product.id
    try:
        yield product_id, user_ids
    finally:
        # Orders first (users cannot be deleted while they have orders); deleting the
        # product removes its stock and cart lines, deleting the users removes their carts.
        with SessionLocal() as db:
            db.execute(delete(Order).where(Order.user_id.in_(user_ids)))
            db.execute(delete(Product).where(Product.id == product_id))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()


def test_two_buyers_cannot_both_get_the_last_unit(last_unit: tuple[int, list[int]]) -> None:
    product_id, user_ids = last_unit
    start_together = threading.Barrier(BUYERS)
    results: dict[int, str] = {}

    def buy(user_id: int) -> None:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            start_together.wait()  # both checkouts start at the same moment
            try:
                order_service.checkout(db, user)
                results[user_id] = "ordered"
            except ConflictError:
                results[user_id] = "out of stock"

    threads = [threading.Thread(target=buy, args=(user_id,)) for user_id in user_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    # Exactly one buyer wins; the other waited for the lock, then saw zero stock.
    assert sorted(results.values()) == ["ordered", "out of stock"]
    with SessionLocal() as db:
        assert db.get(Inventory, product_id).quantity == 0
        orders = db.scalar(select(func.count()).select_from(Order).where(Order.user_id.in_(user_ids)))
        assert orders == 1
