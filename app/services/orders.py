"""Order checkout and order queries.

Checkout is the most important function in the project: it must either do
everything (create the order, take the stock, empty the cart) or nothing.
See docs/checkout.md for a step-by-step explanation.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError
from app.models.cart import Cart, CartItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User
from app.services.cart import get_or_create_cart


def checkout(db: Session, user: User) -> Order:
    """Turn the user's cart into an order in a single database transaction.

    Every change below is part of one transaction: nothing is permanent until
    db.commit(). If anything fails (not enough stock, a database error, a bug),
    db.rollback() undoes all of it, so a half-finished order can never exist.
    """
    cart = get_or_create_cart(db, user)
    if not cart.items:
        raise BadRequestError("Cart is empty")

    try:
        order = _place_order(db, cart)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order


def _place_order(db: Session, cart: Cart) -> Order:
    """Do the checkout steps. The caller commits, or rolls back on any error."""
    # 1. Lock the stock rows of every product in the cart (SELECT ... FOR UPDATE).
    #    Another checkout that wants the same rows now waits until we commit or
    #    roll back, so two customers can never both buy the last unit.
    #    Locking in product_id order means two checkouts always take locks in the
    #    same order, which prevents deadlocks.
    product_ids = sorted(item.product_id for item in cart.items)
    locked_stock = {
        inventory.product_id: inventory
        for inventory in db.scalars(
            select(Inventory)
            .where(Inventory.product_id.in_(product_ids))
            .order_by(Inventory.product_id)
            .with_for_update()
        )
    }

    # 2. Check every line before changing anything.
    for item in cart.items:
        available = locked_stock[item.product_id].quantity
        if item.quantity > available:
            raise ConflictError(
                f"Not enough stock for '{item.product.name}' "
                f"(requested {item.quantity}, available {available})"
            )

    # 3. Create the order, copying each product's name and current price.
    order = Order(user_id=cart.user_id, status=OrderStatus.PLACED, total_amount=Decimal("0"))
    for item in cart.items:
        order.items.append(
            OrderItem(
                product_id=item.product_id,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
            )
        )
    order.total_amount = sum((line.line_total for line in order.items), Decimal("0"))
    db.add(order)
    db.flush()  # Sends the INSERTs now (still inside the uncommitted transaction).

    # 4. Take the stock.
    _reduce_stock(locked_stock, cart.items)

    # 5. Empty the cart (delete-orphan deletes the cart_items rows).
    cart.items.clear()
    db.flush()
    return order


def _reduce_stock(locked_stock: dict[int, Inventory], cart_items: list[CartItem]) -> None:
    """Subtract each cart line's quantity from its (already locked) stock row."""
    for item in cart_items:
        locked_stock[item.product_id].quantity -= item.quantity
