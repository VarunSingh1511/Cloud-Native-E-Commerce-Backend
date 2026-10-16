"""Tests that PostgreSQL itself enforces the data rules, even without the API."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product


def make_product(price: str = "10.00") -> Product:
    return Product(name="Direct insert", description="Bypasses the API", price=Decimal(price))


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
