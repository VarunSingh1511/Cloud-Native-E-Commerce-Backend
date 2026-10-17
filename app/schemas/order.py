"""Response and request schemas for orders."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderItemResponse(BaseModel):
    """One line of an order, exactly as it was bought."""

    model_config = ConfigDict(from_attributes=True)

    # None if the product has since been deleted; the name and price are kept.
    product_id: int | None
    product_name: str
    unit_price: float
    quantity: int
    line_total: float


class OrderResponse(BaseModel):
    """An order with its lines."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: float
    created_at: datetime
    items: list[OrderItemResponse]
