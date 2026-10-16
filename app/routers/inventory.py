"""Inventory REST endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import ADMIN_ONLY_RESPONSES, require_admin
from app.db.session import get_db
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryResponse, InventoryUpdate
from app.services import inventory as inventory_service

router = APIRouter(prefix="/inventory", tags=["Inventory"])

NOT_FOUND_RESPONSE = {404: {"description": "Product not found"}}


@router.get(
    "/{product_id}",
    response_model=InventoryResponse,
    summary="Get a product's stock level",
    responses=NOT_FOUND_RESPONSE,
)
def get_inventory(product_id: int, db: Session = Depends(get_db)) -> Inventory:
    """Return how many units of the product are in stock."""
    return inventory_service.get_inventory(db, product_id)


@router.put(
    "/{product_id}",
    response_model=InventoryResponse,
    summary="Set a product's stock level",
    responses={**NOT_FOUND_RESPONSE, **ADMIN_ONLY_RESPONSES},
    dependencies=[Depends(require_admin)],
)
def set_inventory(
    product_id: int, inventory_data: InventoryUpdate, db: Session = Depends(get_db)
) -> Inventory:
    """Replace the stock level with the given quantity (must be 0 or more)."""
    return inventory_service.set_inventory(db, product_id, inventory_data)
