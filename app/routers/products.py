"""In-memory product REST endpoints for Week 1."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])

_sample_products: list[dict[str, object]] = [
    {
        "id": 1,
        "name": "Laptop",
        "price": 75000.0,
        "description": "Gaming laptop",
    },
    {
        "id": 2,
        "name": "Wireless Mouse",
        "price": 1500.0,
        "description": "Wireless mouse",
    },
]

# This list is deliberately temporary: Week 2 will replace it with database data.
products: list[dict[str, object]] = [product.copy() for product in _sample_products]


def _find_product(product_id: int) -> dict[str, object] | None:
    """Return the matching product, if it is present in the in-memory list."""
    return next((product for product in products if product["id"] == product_id), None)


def reset_products() -> None:
    """Restore initial products; used by automated tests to keep them independent."""
    products[:] = [product.copy() for product in _sample_products]


@router.get("", response_model=list[ProductResponse], summary="List all products")
def get_products() -> list[dict[str, object]]:
    """Return every product currently stored in memory."""
    return products


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    responses={404: {"description": "Product not found"}},
)
def get_product(product_id: int) -> dict[str, object]:
    """Return one product or report that the requested ID does not exist."""
    product = _find_product(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
)
def create_product(product_data: ProductCreate) -> dict[str, object]:
    """Create a product and assign the next available in-memory ID."""
    next_id = max((int(product["id"]) for product in products), default=0) + 1
    product = {"id": next_id, **product_data.model_dump()}
    products.append(product)
    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={404: {"description": "Product not found"}},
)
def update_product(product_id: int, product_data: ProductUpdate) -> dict[str, object]:
    """Replace a product's editable fields."""
    product = _find_product(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.update(product_data.model_dump())
    return product


@router.delete(
    "/{product_id}", summary="Delete a product", responses={404: {"description": "Product not found"}})
def delete_product(product_id: int) -> dict[str, str]:
    """Remove one product from the in-memory list."""
    product = _find_product(product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    products.remove(product)
    return {"message": "Product deleted successfully"}
