"""Stock level for each product (one-to-one with products)."""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Inventory(Base):
    """Kept in its own table so frequent stock updates don't touch product rows."""

    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("quantity >= 0", name="quantity_non_negative"),)

    # The primary key is also the foreign key, so a product can only have one row.
    # ON DELETE CASCADE: deleting a product in SQL also deletes its stock row.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(default=0, server_default="0")

    product: Mapped["Product"] = relationship(back_populates="inventory")
