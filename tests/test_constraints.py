"""Tests that PostgreSQL itself enforces the data rules, even without the API."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User


def make_product(price: str = "10.00") -> Product:
    return Product(name="Direct insert", description="Bypasses the API", price=Decimal(price))


def make_cart_with_product(db_session: Session) -> tuple[Cart, Product]:
    """Insert a user, a cart and a product directly, and return the cart and product."""
    user = User(email="direct@example.com", hashed_password="not-a-real-hash")
    product = make_product()
    db_session.add_all([user, product])
    db_session.flush()
    cart = Cart(user_id=user.id)
    db_session.add(cart)
    db_session.flush()
    return cart, product


def make_order(db_session: Session) -> tuple[Order, Product]:
    """Insert a user, a product and an empty order directly."""
    user = User(email="direct@example.com", hashed_password="not-a-real-hash")
    product = make_product()
    db_session.add_all([user, product])
    db_session.flush()
    order = Order(user_id=user.id, total_amount=Decimal("10.00"))
    db_session.add(order)
    db_session.flush()
    return order, product


def test_database_rejects_zero_or_negative_price(db_session: Session) -> None:
    db_session.add(make_product(price="-1.00"))

    # flush() sends the INSERT now, so the CHECK constraint fails here.
    with pytest.raises(IntegrityError, match="ck_products_price_positive"):
        db_session.flush()


def test_database_rejects_negative_quantity(db_session: Session) -> None:
    product = make_product()
    db_session.add(product)
    db_session.flush()
    db_session.add(Inventory(product_id=product.id, quantity=-1))

    with pytest.raises(IntegrityError, match="ck_inventory_quantity_non_negative"):
        db_session.flush()


def test_database_rejects_zero_quantity_in_cart(db_session: Session) -> None:
    cart, product = make_cart_with_product(db_session)
    db_session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=0))

    with pytest.raises(IntegrityError, match="ck_cart_items_quantity_positive"):
        db_session.flush()


def test_database_rejects_same_product_twice_in_one_cart(db_session: Session) -> None:
    cart, product = make_cart_with_product(db_session)
    db_session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
    db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=2))

    with pytest.raises(IntegrityError, match="uq_cart_items_cart_id_product_id"):
        db_session.flush()


def test_database_rejects_zero_quantity_in_order(db_session: Session) -> None:
    order, product = make_order(db_session)
    db_session.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=0,
        )
    )

    with pytest.raises(IntegrityError, match="ck_order_items_quantity_positive"):
        db_session.flush()


def test_deleting_product_keeps_order_history(db_session: Session) -> None:
    order, product = make_order(db_session)
    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    db_session.add(item)
    db_session.flush()

    db_session.delete(product)
    db_session.flush()
    # Reload from the database to see what ON DELETE SET NULL did.
    db_session.expire_all()

    assert item.product_id is None
    assert item.product_name == "Direct insert"
    assert item.unit_price == Decimal("10.00")


def test_deleting_product_removes_it_from_carts(db_session: Session) -> None:
    cart, product = make_cart_with_product(db_session)
    db_session.add(CartItem(cart_id=cart.id, product_id=product.id, quantity=1))
    db_session.flush()

    db_session.delete(product)
    db_session.flush()
    db_session.expire_all()

    assert cart.items == []
