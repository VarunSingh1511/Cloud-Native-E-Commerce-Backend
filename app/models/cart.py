"""Shopping carts: one cart per user, holding products and quantities."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True: each user has at most one cart. Deleting the user deletes it.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # delete-orphan: an item removed from this list is deleted from the database.
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", order_by="CartItem.id"
    )


class CartItem(Base):
    """One product line in a cart."""

    __tablename__ = "cart_items"
    __table_args__ = (
        # The same product can appear only once per cart; adding it again
        # increases the quantity instead of creating a second line.
        UniqueConstraint("cart_id", "product_id"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    # If an admin deletes the product, it simply disappears from every cart.
    # Indexed so that delete can find those cart lines quickly.
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    quantity: Mapped[int]

    cart: Mapped[Cart] = relationship(back_populates="items")
    # Used to show the product's current name and price in the cart.
    product: Mapped["Product"] = relationship()
