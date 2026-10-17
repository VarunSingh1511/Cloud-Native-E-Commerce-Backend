"""Request and response schemas for the shopping cart."""

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    """A product to add to the cart."""

    product_id: int
    # le: a sanity limit per request, so a typo cannot add millions of units.
    quantity: int = Field(default=1, ge=1, le=1000)


class CartItemResponse(BaseModel):
    """One line of the cart, priced at the product's *current* price."""

    id: int
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    line_total: float


class CartResponse(BaseModel):
    """The whole cart with its total."""

    items: list[CartItemResponse]
    total: float
