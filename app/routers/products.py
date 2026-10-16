"""Product REST endpoints backed by PostgreSQL."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["Products"])

# Shown in Swagger; the actual 404 comes from NotFoundError raised in the service.
NOT_FOUND_RESPONSE = {404: {"description": "Product not found"}}
BAD_CATEGORY_RESPONSE = {400: {"description": "category_id does not exist"}}


@router.get("", response_model=list[ProductResponse], summary="List all products")
def get_products(db: Session = Depends(get_db)) -> list[Product]:
    """Return every product in the database."""
    return product_service.list_products(db)


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
    responses=BAD_CATEGORY_RESPONSE,
)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """Create a product; the database assigns its ID."""
    return product_service.create_product(db, product_data)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={**NOT_FOUND_RESPONSE, **BAD_CATEGORY_RESPONSE},
)
def update_product(
    product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    """Replace a product's editable fields."""
    return product_service.update_product(db, product_id, product_data)


@router.delete("/{product_id}", summary="Delete a product", responses=NOT_FOUND_RESPONSE)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Remove one product from the database."""
    product_service.delete_product(db, product_id)
    return {"message": "Product deleted successfully"}
