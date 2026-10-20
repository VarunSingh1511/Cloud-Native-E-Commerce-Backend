"""Request and response schemas for products."""

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Fields and validation rules shared by product create and update requests."""

    name: str = Field(min_length=1, max_length=100)
    # le: the largest value NUMERIC(10, 2) can store; larger values would make the DB fail.
    price: float = Field(gt=0, le=99_999_999.99)
    description: str = Field(min_length=1, max_length=500)
    # Optional: a product does not have to belong to a category.
    category_id: int | None = None


class ProductCreate(ProductBase):
    """Data a client supplies when creating a product."""


class ProductUpdate(ProductBase):
    """Replacement data supplied when updating a product with PUT."""


class ProductResponse(BaseModel):
    """Product data returned by the API, including its database-generated ID."""

    # Lets Pydantic read attributes from SQLAlchemy objects (product.name),
    # not only from dicts. The NUMERIC price from the DB is returned as a float.
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(gt=0)
    name: str
    price: float
    description: str
    category_id: int | None
    # Public URL of the product image, or None if no image was uploaded.
    image_url: str | None = None
