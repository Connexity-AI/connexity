"""Which workspaces a person can reach, and opening and creating them.

A workspace is a company (Decided 2026-11-12). This module is the only place that
decides access, on the web and through MCP: a person reaches the workspaces they are a
member of (`workspace_member`) in an agency they are in (`agency_member`). Those rows
follow the person's place in the workspace's
agency and are written by `app/crud/agency.py`; a new workspace is made there too
(`add_workspace`). `user.company_id` is the workspace the person has open
on the web; every web route scopes by it.
"""

import uuid

from sqlmodel import Session, col, func, select

from app.models.agency import AgencyMember
from app.models.company import Company
from app.models.user import User
from app.models.workspace_member import WorkspaceMember

# A workspace row counts only for a person who is in the workspace's agency, so a row
# left behind could never give access on its own.
_IN_ITS_AGENCY = (col(AgencyMember.agency_id) == col(Company.agency_id)) & (
    col(AgencyMember.user_id) == col(WorkspaceMember.user_id)
)


def list_accessible_workspaces(*, session: Session, user: User) -> list[Company]:
    return list(
        session.exec(
            select(Company)
            .join(WorkspaceMember, col(WorkspaceMember.company_id) == Company.id)
            .join(AgencyMember, _IN_ITS_AGENCY)
            .where(WorkspaceMember.user_id == user.id)
            .order_by(func.lower(Company.name), col(Company.id))
        ).all()
    )


def get_accessible_workspace(
    *, session: Session, user: User, workspace_id: uuid.UUID
) -> Company | None:
    """The workspace, or None when it does not exist or the person cannot reach it."""
    return session.exec(
        select(Company)
        .join(WorkspaceMember, col(WorkspaceMember.company_id) == Company.id)
        .join(AgencyMember, _IN_ITS_AGENCY)
        .where(WorkspaceMember.user_id == user.id, Company.id == workspace_id)
    ).first()


def is_member_of_all(
    *, session: Session, user: User, workspace_ids: set[uuid.UUID]
) -> bool:
    """Whether the person is a member of every one of these workspaces (one query)."""
    found = session.exec(
        select(func.count())
        .select_from(WorkspaceMember)
        .join(Company, col(Company.id) == WorkspaceMember.company_id)
        .join(AgencyMember, _IN_ITS_AGENCY)
        .where(
            WorkspaceMember.user_id == user.id,
            col(WorkspaceMember.company_id).in_(workspace_ids),
        )
    ).one()
    return found == len(workspace_ids)


def open_workspace(*, session: Session, user: User, workspace: Company) -> User:
    """Make the workspace the one this person has open on the web.

    The caller must have checked access with `get_accessible_workspace`.
    """
    user.company_id = workspace.id
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
