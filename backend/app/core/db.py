from sqlmodel import Session, create_engine

from app import crud
from app.core.config import settings
from app.models import UserCreate

if not settings.SQLALCHEMY_DATABASE_URI:
    raise RuntimeError("DATABASE_URL or POSTGRES_* env vars must be configured")
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    """Ensure the admin superuser exists. Safe to run on every boot."""
    # Credentials come from .env — defaults: admin@example.com / password
    if not crud.get_user_by_email(session=session, email=settings.FIRST_SUPERUSER):
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
            full_name="Admin",
        )
        crud.create_user(session=session, user_create=user_in)

    session.commit()
