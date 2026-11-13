"""The fixed categories (`app/models/category.py`)."""

import uuid

from sqlmodel import Session, col, select

from app.models.category import Category


def list_categories(*, session: Session) -> list[Category]:
    """Every category, in its fixed order."""
    return list(
        session.exec(
            select(Category).order_by(col(Category.position), col(Category.key))
        ).all()
    )


def categories_by_id(*, session: Session) -> dict[uuid.UUID, Category]:
    return {category.id: category for category in list_categories(session=session)}
