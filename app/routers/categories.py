"""Category REST endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services import categories as category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryResponse], summary="List all categories")
def get_categories(db: Session = Depends(get_db)) -> list[Category]:
    """Return every category, sorted by name."""
    return category_service.list_categories(db)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get a category by ID",
    responses={404: {"description": "Category not found"}},
)
def get_category(category_id: int, db: Session = Depends(get_db)) -> Category:
    """Return one category."""
    return category_service.get_category(db, category_id)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
    responses={409: {"description": "A category with this name already exists"}},
)
def create_category(category_data: CategoryCreate, db: Session = Depends(get_db)) -> Category:
    """Create a category with a unique name."""
    return category_service.create_category(db, category_data)
