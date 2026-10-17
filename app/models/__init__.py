"""SQLAlchemy models.

Importing every model here registers its table on `Base.metadata`, which is
what Alembic reads when autogenerating migrations.
"""

from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole

__all__ = [
    "Cart",
    "CartItem",
    "Category",
    "Inventory",
    "Order",
    "OrderItem",
    "OrderStatus",
    "Product",
    "User",
    "UserRole",
]
