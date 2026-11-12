"""Which workspaces a person can reach.

A workspace is a company (Decided 2026-11-12). Every MCP call is scoped to one, and
this module is the only place that decides access. Today a person reaches exactly
their own company; memberships across several workspaces replace that here.
"""

import uuid

from sqlmodel import Session

from app.models.company import Company
from app.models.user import User


def list_accessible_workspaces(*, session: Session, user: User) -> list[Company]:
    company = session.get(Company, user.company_id)
    return [company] if company is not None else []


def get_accessible_workspace(
    *, session: Session, user: User, workspace_id: uuid.UUID
) -> Company | None:
    """The workspace, or None when it does not exist or the person cannot reach it."""
    for workspace in list_accessible_workspaces(session=session, user=user):
        if workspace.id == workspace_id:
            return workspace
    return None
