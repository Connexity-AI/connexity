from sqlmodel import create_engine

from app.core.config import settings

if not settings.SQLALCHEMY_DATABASE_URI:
    raise RuntimeError("DATABASE_URL or POSTGRES_* env vars must be configured")
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28
