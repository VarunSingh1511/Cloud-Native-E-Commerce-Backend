"""Products in the catalog."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.inventory import Inventory


class Product(Base):
    __tablename__ = "products"
    # Enforced by PostgreSQL itself, even for data that bypasses the API.
    # The naming convention turns this into "ck_products_price_positive".
    __table_args__ = (CheckConstraint("price > 0", name="price_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    # NUMERIC(10, 2) stores exact money values (floats can round, e.g. 0.1 + 0.2).
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    # Optional link to a category. If the category is deleted, the product stays
    # but its category_id becomes NULL. PostgreSQL does not index foreign keys
    # automatically, so index=True speeds up "products in category X" queries.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Public URL of the product's image in Azure Blob Storage (Week 9), or None.
    image_url: Mapped[str | None] = mapped_column(String(500))

    category: Mapped["Category | None"] = relationship(back_populates="products")
    # One-to-one: each product has at most one inventory row. Deleting the product
    # through the ORM also deletes its inventory row.
    inventory: Mapped["Inventory | None"] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
