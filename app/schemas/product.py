"""Request and response schemas for products."""

from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """Fields and validation rules shared by product create and update requests."""

    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)


class ProductCreate(ProductBase):
    """Data a client supplies when creating a product."""


class ProductUpdate(ProductBase):
    """Replacement data supplied when updating a product with PUT."""


class ProductResponse(BaseModel):
    """Product data returned by the API, including its application-generated ID."""

    id: int = Field(gt=0)
    name: str
    price: float
    description: str
