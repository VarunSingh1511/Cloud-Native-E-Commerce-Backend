"""add check constraints and backfill inventory

Written by hand: Alembic autogenerate does not detect CHECK constraints.

Revision ID: 22d1fd6d142c
Revises: fadf75fe9183
Create Date: 2026-10-16 21:51:19.843002

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '22d1fd6d142c'
down_revision: Union[str, Sequence[str], None] = 'fadf75fe9183'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add CHECK constraints and give every existing product an inventory row."""
    # op.f() marks the name as final, so it is used exactly as written and
    # matches the names the models produce through the naming convention.
    op.create_check_constraint(op.f("ck_products_price_positive"), "products", "price > 0")
    op.create_check_constraint(
        op.f("ck_inventory_quantity_non_negative"), "inventory", "quantity >= 0"
    )

    # Data migration: from now on the app creates an inventory row with every
    # product, so add the missing rows for products created before this change.
    op.execute(
        """
        INSERT INTO inventory (product_id, quantity)
        SELECT id, 0 FROM products
        WHERE id NOT IN (SELECT product_id FROM inventory)
        """
    )


def downgrade() -> None:
    """Remove the CHECK constraints.

    Backfilled inventory rows are kept: they are valid data under the old schema too.
    """
    op.drop_constraint(op.f("ck_inventory_quantity_non_negative"), "inventory", type_="check")
    op.drop_constraint(op.f("ck_products_price_positive"), "products", type_="check")
