"""Request and response schemas for categories."""

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    """Data a client supplies when creating a category."""

    # Strip surrounding spaces first, so a name of only spaces is rejected as empty.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)


class CategoryResponse(BaseModel):
    """Category data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
