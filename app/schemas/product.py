"""Request and response schemas for products."""

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Data a client supplies when creating a product."""

    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)


class ProductUpdate(BaseModel):
    """Replacement data supplied when updating a product with PUT."""

    name: str = Field(min_length=1, max_length=100)
    price: float = Field(gt=0)
    description: str = Field(min_length=1, max_length=500)


class ProductResponse(BaseModel):
    """Product data returned by the API, including its application-generated ID."""

    id: int = Field(gt=0)
    name: str
    price: float
    description: str
