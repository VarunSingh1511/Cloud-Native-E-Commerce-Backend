"""Category database operations."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.category import Category
from app.schemas.category import CategoryCreate


def list_categories(db: Session) -> list[Category]:
    """Return all categories in alphabetical order."""
    return list(db.scalars(select(Category).order_by(Category.name)))


def get_category(db: Session, category_id: int) -> Category:
    """Return one category, or raise NotFoundError."""
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category")
    return category


def create_category(db: Session, category_data: CategoryCreate) -> Category:
    """Insert a category; raise ConflictError if the name is already taken."""
    category = Category(name=category_data.name)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        # The unique constraint on categories.name rejected the insert. Relying on
        # the database (instead of checking with a SELECT first) is also safe when
        # two requests try to create the same name at the same moment.
        db.rollback()
        raise ConflictError(f"Category '{category_data.name}' already exists")
    db.refresh(category)
    return category
