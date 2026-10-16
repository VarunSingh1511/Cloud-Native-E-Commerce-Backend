"""Product REST endpoints backed by PostgreSQL."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["Products"])

PRODUCT_NOT_FOUND = "Product not found"


@router.get("", response_model=list[ProductResponse], summary="List all products")
def get_products(db: Session = Depends(get_db)) -> list[Product]:
    """Return every product in the database."""
    return product_service.list_products(db)


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def get_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    """Return one product or report that the requested ID does not exist."""
    product = product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)) -> Product:
    """Create a product; the database assigns its ID."""
    return product_service.create_product(db, product_data)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={404: {"description": PRODUCT_NOT_FOUND}},
)
def update_product(
    product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    """Replace a product's editable fields."""
    product = product_service.update_product(db, product_id, product_data)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
    return product


@router.delete(
    "/{product_id}", summary="Delete a product", responses={404: {"description": PRODUCT_NOT_FOUND}}
)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    """Remove one product from the database."""
    if not product_service.delete_product(db, product_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRODUCT_NOT_FOUND)
    return {"message": "Product deleted successfully"}
