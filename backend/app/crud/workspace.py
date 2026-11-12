"""Which workspaces a person can reach, and opening and creating them.

A workspace is a company (Decided 2026-11-12). This module is the only place that
decides access, on the web and through MCP: a person reaches the workspaces they are a
member of (`workspace_member`). `user.company_id` is the workspace the person has open
on the web; every web route scopes by it.
"""

import uuid

from sqlmodel import Session, col, func, select

from app.models.company import Company
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


def list_accessible_workspaces(*, session: Session, user: User) -> list[Company]:
    return list(
        session.exec(
            select(Company)
            .join(WorkspaceMember, col(WorkspaceMember.company_id) == Company.id)
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
        .where(WorkspaceMember.user_id == user.id, Company.id == workspace_id)
    ).first()


def is_member_of_all(
    *, session: Session, user: User, workspace_ids: set[uuid.UUID]
) -> bool:
    """Whether the person is a member of every one of these workspaces (one query)."""
    found = session.exec(
        select(func.count())
        .select_from(WorkspaceMember)
        .where(
            WorkspaceMember.user_id == user.id,
            col(WorkspaceMember.company_id).in_(workspace_ids),
        )
    ).one()
    return found == len(workspace_ids)


def add_member(*, session: Session, user_id: uuid.UUID, company_id: uuid.UUID) -> None:
    """Make a person a member of a workspace; does nothing when they already are."""
    if session.get(WorkspaceMember, (user_id, company_id)) is None:
        session.add(WorkspaceMember(user_id=user_id, company_id=company_id))


def create_workspace(*, session: Session, user: User, name: str) -> Company:
    """A new workspace with the person as its member. It is not opened."""
    workspace = Company(name=name.strip())
    session.add(workspace)
    session.flush()
    add_member(session=session, user_id=user.id, company_id=workspace.id)
    session.commit()
    session.refresh(workspace)
    return workspace


def open_workspace(*, session: Session, user: User, workspace: Company) -> User:
    """Make the workspace the one this person has open on the web.

    The caller must have checked access with `get_accessible_workspace`.
    """
    user.company_id = workspace.id
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
