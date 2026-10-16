"""Product REST endpoints backed by PostgreSQL."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import ADMIN_ONLY_RESPONSES, require_admin
from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["Products"])

# Shown in Swagger; the actual 404 comes from NotFoundError raised in the service.
NOT_FOUND_RESPONSE = {404: {"description": "Product not found"}}
BAD_CATEGORY_RESPONSE = {400: {"description": "category_id does not exist"}}


@router.get("", response_model=list[ProductResponse], summary="List products")
def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip (for paging)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of products to return"),
    category_id: int | None = Query(None, description="Only products in this category"),
    q: str | None = Query(
        None, min_length=1, max_length=100, description="Case-insensitive name search"
    ),
    db: Session = Depends(get_db),
) -> list[Product]:
    """Return one page of products, optionally filtered by category and name."""
    return product_service.list_products(
        db, skip=skip, limit=limit, category_id=category_id, q=q
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    responses=NOT_FOUND_RESPONSE,
)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    """Return one product."""
    return product_service.get_product(db, product_id)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    responses={**BAD_CATEGORY_RESPONSE, **ADMIN_ONLY_RESPONSES},
    dependencies=[Depends(require_admin)],
)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """Create a product; the database assigns its ID."""
    return product_service.create_product(db, product_data)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={**NOT_FOUND_RESPONSE, **BAD_CATEGORY_RESPONSE, **ADMIN_ONLY_RESPONSES},
    dependencies=[Depends(require_admin)],
)
def update_product(
    product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    """Replace a product's editable fields."""
    return product_service.update_product(db, product_id, product_data)


@router.delete(
    "/{product_id}",
    summary="Delete a product",
    responses={**NOT_FOUND_RESPONSE, **ADMIN_ONLY_RESPONSES},
    dependencies=[Depends(require_admin)],
)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Remove one product from the database."""
    product_service.delete_product(db, product_id)
    return {"message": "Product deleted successfully"}
