"""Column types shared by table models."""

import enum
from typing import Any

from sqlalchemy import Enum as SAEnum

ENUM_COLUMN_LENGTH = 32


def enum_type(enum_cls: type[enum.Enum]) -> Any:
    """SQLAlchemy type for an enum column: a VARCHAR holding the member's value.

    One rule for every enum column. Values (not member names) are stored so the
    database matches the API, and no Postgres ENUM type is created, so adding a
    member needs no ``ALTER TYPE`` migration.

    Returns ``Any`` because SQLModel types ``sa_type`` as a class, not an instance.
    """
    return SAEnum(
        enum_cls,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        length=ENUM_COLUMN_LENGTH,
        validate_strings=True,
    )
