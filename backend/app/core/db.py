from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app import crud
from app.core.config import settings
from app.models import UserCreate

if settings.SQLALCHEMY_DATABASE_URI:
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
else:
    # placeholder, to prevent exceptions for None
    engine = create_engine("sqlite:///:memory:")


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28

def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    # Wipe everything
    truncate_all_tables(session)

    # Seed one superuser
    # Credentials come from .env — defaults: admin@example.com / password
    user_in = UserCreate(
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        is_superuser=True,
        full_name="Admin",
    )
    crud.create_user(session=session, user_create=user_in)

    session.commit()


def truncate_all_tables(session: Session) -> None:
    """
    Truncate all SQLModel tables dynamically.
    """
    table_names = ", ".join(
        f'"{table.name}"' for table in SQLModel.metadata.sorted_tables
    )

    session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE;"))
    session.commit()
