"""Shopping cart endpoints. Each logged-in user has their own cart."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartResponse
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])

NOT_LOGGED_IN_RESPONSE = {401: {"description": "Not logged in"}}


@router.get(
    "", response_model=CartResponse, summary="View my cart", responses=NOT_LOGGED_IN_RESPONSE
)
def get_cart(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartResponse:
    """Return the cart with current prices and the total."""
    cart = cart_service.get_or_create_cart(db, current_user)
    return cart_service.build_cart_response(cart)


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a product to my cart",
    responses={**NOT_LOGGED_IN_RESPONSE, 400: {"description": "Product does not exist"}},
)
def add_cart_item(
    item_data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartResponse:
    """Add a product, or increase its quantity if it is already in the cart.

    Stock is not reserved here; it is checked when the order is placed.
    """
    cart = cart_service.add_item(db, current_user, item_data)
    return cart_service.build_cart_response(cart)


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a line from my cart",
    responses={**NOT_LOGGED_IN_RESPONSE, 404: {"description": "Cart item not found"}},
)
def remove_cart_item(
    item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> None:
    """Remove one line (all of its quantity) from the cart."""
    cart_service.remove_item(db, current_user, item_id)
