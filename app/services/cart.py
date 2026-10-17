"""Shopping cart operations. Every function works on the given user's own cart."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.models.cart import Cart, CartItem
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemResponse, CartResponse


def get_or_create_cart(db: Session, user: User) -> Cart:
    """Return the user's cart, creating an empty one the first time it is needed."""
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is not None:
        return cart
    cart = Cart(user_id=user.id)
    db.add(cart)
    try:
        db.commit()
    except IntegrityError:
        # Another request created this user's cart at the same moment (carts.user_id
        # is unique). Use that one instead of failing.
        db.rollback()
        return db.scalars(select(Cart).where(Cart.user_id == user.id)).one()
    db.refresh(cart)
    return cart


def add_item(db: Session, user: User, item_data: CartItemCreate) -> Cart:
    """Add a product to the cart; if it is already there, increase its quantity."""
    if db.get(Product, item_data.product_id) is None:
        raise BadRequestError(f"Product {item_data.product_id} does not exist")
    cart = get_or_create_cart(db, user)
    existing = next((item for item in cart.items if item.product_id == item_data.product_id), None)
    if existing is not None:
        existing.quantity += item_data.quantity
    else:
        cart.items.append(CartItem(product_id=item_data.product_id, quantity=item_data.quantity))
    db.commit()
    return cart


def remove_item(db: Session, user: User, item_id: int) -> None:
    """Remove one line from the user's own cart.

    An item that belongs to someone else's cart is reported as "not found", so
    users cannot discover or touch other carts.
    """
    cart = get_or_create_cart(db, user)
    item = next((item for item in cart.items if item.id == item_id), None)
    if item is None:
        raise NotFoundError("Cart item")
    # Removing it from the list deletes the row (cascade="all, delete-orphan").
    cart.items.remove(item)
    db.commit()


def build_cart_response(cart: Cart) -> CartResponse:
    """Price every line at the product's current price and add up the total.

    Money is calculated with Decimal (exact) and only converted to a JSON
    number in the response.
    """
    items = []
    total = Decimal("0")
    for item in cart.items:
        line_total = item.product.price * item.quantity
        total += line_total
        items.append(
            CartItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name,
                unit_price=float(item.product.price),
                quantity=item.quantity,
                line_total=float(line_total),
            )
        )
    return CartResponse(items=items, total=float(total))
