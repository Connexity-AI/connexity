"""CRUD for the ``company`` table (a workspace)."""

import uuid

from sqlmodel import Session

from app.models.company import Company


def get_company(*, session: Session, company_id: uuid.UUID) -> Company | None:
    return session.get(Company, company_id)
