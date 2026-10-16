"""Request and response schemas for inventory (stock levels)."""

from pydantic import BaseModel, ConfigDict, Field


class InventoryUpdate(BaseModel):
    """New absolute stock level for a product."""

    quantity: int = Field(ge=0)


class InventoryResponse(BaseModel):
    """Current stock level of a product."""

    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
