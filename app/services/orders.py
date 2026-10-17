"""Order checkout and order queries.

Checkout is the most important function in the project: it must either do
everything (create the order, take the stock, empty the cart) or nothing.
See docs/checkout.md for a step-by-step explanation.
"""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.cart import Cart, CartItem
from app.models.inventory import Inventory
from app.models.order import Order, OrderItem, OrderStatus
from app.models.user import User, UserRole
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


# Which status an order may move to from each status. DELIVERED and CANCELLED
# are final. A shipped order can no longer be cancelled.
ALLOWED_STATUS_CHANGES: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PLACED: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def change_status(db: Session, order_id: int, new_status: OrderStatus) -> Order:
    """Move an order to a new status (admin action), in one transaction.

    Cancelling puts the ordered quantities back into stock. The order row is
    locked first, so two admins cancelling at the same moment cannot restock twice.
    """
    order = db.get(Order, order_id, with_for_update=True)
    if order is None:
        raise NotFoundError("Order")
    if new_status not in ALLOWED_STATUS_CHANGES[order.status]:
        raise ConflictError(
            f"Cannot change order status from {order.status.value} to {new_status.value}"
        )

    try:
        if new_status == OrderStatus.CANCELLED:
            _restock(db, order)
        order.status = new_status
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)
    return order


def _restock(db: Session, order: Order) -> None:
    """Return each line's quantity to stock. Lines whose product was deleted are skipped."""
    for line in order.items:
        if line.product_id is None:
            continue
        inventory = db.get(Inventory, line.product_id, with_for_update=True)
        if inventory is not None:
            inventory.quantity += line.quantity


def list_orders(db: Session, user: User) -> list[Order]:
    """Return orders, newest first: all orders for an admin, otherwise only the user's own."""
    query = (
        select(Order)
        # Load every order's items in one extra query, instead of one query per
        # order when the response is built (the "N+1 queries" problem).
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc(), Order.id.desc())
    )
    if user.role != UserRole.ADMIN:
        query = query.where(Order.user_id == user.id)
    return list(db.scalars(query))


def get_order(db: Session, user: User, order_id: int) -> Order:
    """Return one order if the user may see it.

    Another customer's order is reported as "not found" (404), not "forbidden"
    (403), so nobody can learn which order IDs exist.
    """
    order = db.get(Order, order_id)
    if order is None or (user.role != UserRole.ADMIN and order.user_id != user.id):
        raise NotFoundError("Order")
    return order
