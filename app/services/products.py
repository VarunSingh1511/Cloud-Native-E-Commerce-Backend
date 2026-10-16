"""Product database operations. Routers call these and handle HTTP concerns."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def _check_category_exists(db: Session, category_id: int | None) -> None:
    """Reject a category_id that points to no category.

    This is a 400 (bad request body), not a 404: the URL itself was valid.
    """
    if category_id is not None and db.get(Category, category_id) is None:
        raise BadRequestError(f"Category {category_id} does not exist")


def list_products(db: Session) -> list[Product]:
    """Return all products, oldest first."""
    return list(db.scalars(select(Product).order_by(Product.id)))


def get_product(db: Session, product_id: int) -> Product:
    """Return one product by primary key, or raise NotFoundError."""
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError("Product")
    return product


def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Insert a new product and return it with its database-generated ID."""
    _check_category_exists(db, product_data.category_id)
    values = product_data.model_dump()
    # Convert via str so 19.99 becomes Decimal("19.99"), not a long binary float.
    values["price"] = Decimal(str(values["price"]))
    # Every product starts with a stock row of 0. Both rows are inserted by the
    # same commit, so either both exist or neither does.
    product = Product(**values, inventory=Inventory(quantity=0))
    db.add(product)
    db.commit()
    # Reload from the DB to get server-generated values (id, created_at).
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_data: ProductUpdate) -> Product:
    """Replace a product's editable fields."""
    product = get_product(db, product_id)
    _check_category_exists(db, product_data.category_id)
    product.name = product_data.name
    product.description = product_data.description
    product.price = Decimal(str(product_data.price))
    product.category_id = product_data.category_id
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> None:
    """Delete a product."""
    product = get_product(db, product_id)
    db.delete(product)
    db.commit()
