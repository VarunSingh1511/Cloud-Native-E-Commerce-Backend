"""Product database operations. Routers call these and handle HTTP concerns."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def list_products(db: Session) -> list[Product]:
    """Return all products, oldest first."""
    return list(db.scalars(select(Product).order_by(Product.id)))


def get_product(db: Session, product_id: int) -> Product | None:
    """Return one product by primary key, or None if it does not exist."""
    return db.get(Product, product_id)


def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Insert a new product and return it with its database-generated ID."""
    values = product_data.model_dump()
    # Convert via str so 19.99 becomes Decimal("19.99"), not a long binary float.
    values["price"] = Decimal(str(values["price"]))
    product = Product(**values)
    db.add(product)
    db.commit()
    # Reload from the DB to get server-generated values (id, created_at).
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Product | None:
    """Replace a product's editable fields; return None if it does not exist."""
    product = db.get(Product, product_id)
    if product is None:
        return None
    product.name = product_data.name
    product.description = product_data.description
    product.price = Decimal(str(product_data.price))
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete a product; return False if it does not exist."""
    product = db.get(Product, product_id)
    if product is None:
        return False
    db.delete(product)
    db.commit()
    return True
