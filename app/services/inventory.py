"""Inventory (stock level) database operations."""

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryUpdate
from app.services.products import get_product


def get_inventory(db: Session, product_id: int) -> Inventory:
    """Return a product's stock row; raise NotFoundError if the product does not exist."""
    get_product(db, product_id)  # raises NotFoundError("Product") for an unknown ID
    # Every product gets an inventory row when it is created (and older products
    # were backfilled by a migration), so this lookup is expected to succeed.
    inventory = db.get(Inventory, product_id)
    if inventory is None:
        raise NotFoundError("Inventory")
    return inventory


def set_inventory(db: Session, product_id: int, inventory_data: InventoryUpdate) -> Inventory:
    """Set a product's stock to an absolute quantity."""
    inventory = get_inventory(db, product_id)
    inventory.quantity = inventory_data.quantity
    db.commit()
    db.refresh(inventory)
    return inventory
