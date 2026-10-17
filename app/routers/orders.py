"""Order endpoints: checkout and order history."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderResponse
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order from my cart (checkout)",
    responses={
        400: {"description": "Cart is empty"},
        401: {"description": "Not logged in"},
        409: {"description": "Not enough stock for a product in the cart"},
    },
)
def place_order(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Order:
    """Buy everything in the cart at current prices.

    In one transaction: checks and takes the stock, creates the order, and empties
    the cart. If any product is short, nothing changes.
    """
    return order_service.checkout(db, current_user)


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="List orders (my own, or all orders for an admin)",
    responses={401: {"description": "Not logged in"}},
)
def list_orders(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Order]:
    """Customers see their own orders; admins see every order. Newest first."""
    return order_service.list_orders(db, current_user)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get one order",
    responses={401: {"description": "Not logged in"}, 404: {"description": "Order not found"}},
)
def get_order(
    order_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Order:
    """Return an order. Customers can only open their own orders."""
    return order_service.get_order(db, current_user, order_id)
