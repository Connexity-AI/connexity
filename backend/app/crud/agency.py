"""Agencies and the people in them.

`agency_member` says what a person is in an agency: their role, whether they reach all
of its workspaces or chosen ones, and whether they can approve. Access itself is still
read from `workspace_member` (`app/crud/workspace.py`); this module is the only place
that writes those rows for a person in an agency, so the two cannot drift:

- "all workspaces": a row for every workspace of the agency, added again whenever a
  workspace is created;
- chosen workspaces: exactly the chosen rows.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import delete
from sqlmodel import Session, col, func, select

from app.models.agency import Agency, AgencyMember, AgencyRole
from app.models.company import Company, workspace_name_from_email
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


class LastAdminError(Exception):
    """The change would leave the agency without an Admin."""


class UnknownWorkspaceError(Exception):
    """A chosen workspace does not belong to the agency."""


@dataclass(frozen=True)
class MemberRow:
    user: User
    member: AgencyMember
    workspace_ids: list[uuid.UUID]


def new_agency(*, session: Session, email: str) -> Agency:
    """An agency with nobody in it yet, for a person who is about to be created."""
    agency = Agency(name=workspace_name_from_email(email))
    session.add(agency)
    session.flush()
    return agency


def get_membership(
    *, session: Session, user_id: uuid.UUID, agency_id: uuid.UUID
) -> AgencyMember | None:
    return session.get(AgencyMember, (agency_id, user_id))


def list_agencies(*, session: Session, user: User) -> list[tuple[Agency, AgencyMember]]:
    rows = session.exec(
        select(Agency, AgencyMember)
        .join(AgencyMember, col(AgencyMember.agency_id) == Agency.id)
        .where(AgencyMember.user_id == user.id)
        .order_by(func.lower(Agency.name), col(Agency.id))
    ).all()
    return [(row[0], row[1]) for row in rows]


def agency_workspaces(*, session: Session, agency_id: uuid.UUID) -> list[Company]:
    return list(
        session.exec(
            select(Company)
            .where(Company.agency_id == agency_id)
            .order_by(func.lower(Company.name), col(Company.id))
        ).all()
    )


def admins(*, session: Session, agency_id: uuid.UUID) -> list[User]:
    return list(
        session.exec(
            select(User)
            .join(AgencyMember, col(AgencyMember.user_id) == User.id)
            .where(
                AgencyMember.agency_id == agency_id,
                AgencyMember.role == AgencyRole.admin,
            )
            .order_by(func.lower(User.email))
        ).all()
    )


def list_members(*, session: Session, agency_id: uuid.UUID) -> list[MemberRow]:
    """Everyone in the agency with the workspaces each reaches, Admins first."""
    people = session.exec(
        select(User, AgencyMember)
        .join(AgencyMember, col(AgencyMember.user_id) == User.id)
        .where(AgencyMember.agency_id == agency_id)
        .order_by(col(AgencyMember.role), func.lower(User.email))
    ).all()
    reach = session.exec(
        select(WorkspaceMember.user_id, WorkspaceMember.company_id)
        .join(Company, col(Company.id) == WorkspaceMember.company_id)
        .where(Company.agency_id == agency_id)
        .order_by(func.lower(Company.name), col(Company.id))
    ).all()
    by_person: dict[uuid.UUID, list[uuid.UUID]] = {}
    for user_id, company_id in reach:
        by_person.setdefault(user_id, []).append(company_id)
    return [
        MemberRow(user=user, member=member, workspace_ids=by_person.get(user.id, []))
        for user, member in people
    ]


def add_workspace(
    *, session: Session, agency: Agency, name: str, created_by: User
) -> Company:
    """A new workspace in the agency. Everyone with "all workspaces" reaches it, and
    so does the person who made it. It is not opened. Commits."""
    workspace = Company(name=name.strip(), agency_id=agency.id)
    session.add(workspace)
    session.flush()
    reaching = set(
        session.exec(
            select(AgencyMember.user_id).where(
                AgencyMember.agency_id == agency.id,
                col(AgencyMember.all_workspaces).is_(True),
            )
        ).all()
    )
    reaching.add(created_by.id)
    for user_id in reaching:
        session.add(WorkspaceMember(user_id=user_id, company_id=workspace.id))
    session.commit()
    session.refresh(workspace)
    return workspace


def rename_agency(*, session: Session, agency: Agency, name: str) -> Agency:
    agency.name = name.strip()
    session.add(agency)
    session.commit()
    session.refresh(agency)
    return agency


def update_member(
    *,
    session: Session,
    agency: Agency,
    member: AgencyMember,
    role: AgencyRole | None = None,
    all_workspaces: bool | None = None,
    workspace_ids: list[uuid.UUID] | None = None,
    can_approve: bool | None = None,
) -> AgencyMember:
    """Change what a person is in the agency; only what is given changes. Commits.

    Raises:
        LastAdminError: the person is the only Admin and would stop being one.
        UnknownWorkspaceError: a chosen workspace is not one of the agency's.
    """
    if (
        role is not None
        and role != AgencyRole.admin
        and member.role == AgencyRole.admin
        and _is_last_admin(session=session, member=member)
    ):
        raise LastAdminError
    if role is not None:
        member.role = role
    if can_approve is not None:
        member.can_approve = can_approve

    if all_workspaces is not None or workspace_ids is not None:
        # Workspaces named without saying "all" or "chosen" means chosen.
        reaches_all = all_workspaces if all_workspaces is not None else False
        owned = {w.id for w in agency_workspaces(session=session, agency_id=agency.id)}
        if reaches_all:
            chosen = owned
        elif workspace_ids is None:
            # Switched to chosen workspaces without naming any: keep what they reach.
            chosen = _reached(session=session, member=member, owned=owned)
        else:
            chosen = set(workspace_ids)
            if not chosen <= owned:
                raise UnknownWorkspaceError
        member.all_workspaces = reaches_all
        _set_reach(session=session, member=member, owned=owned, chosen=chosen)

    session.add(member)
    session.commit()
    session.refresh(member)
    _reopen_if_needed(session=session, user_id=member.user_id)
    return member


def remove_member(*, session: Session, agency: Agency, member: AgencyMember) -> None:
    """Take a person out of the agency: they lose its workspaces at once, on the web
    and for their assistants. What they did stays on record. Commits.

    Raises:
        LastAdminError: the person is the agency's only Admin.
    """
    if member.role == AgencyRole.admin and _is_last_admin(
        session=session, member=member
    ):
        raise LastAdminError
    user_id = member.user_id
    owned = {w.id for w in agency_workspaces(session=session, agency_id=agency.id)}
    _set_reach(session=session, member=member, owned=owned, chosen=set())
    session.delete(member)
    session.commit()
    _reopen_if_needed(session=session, user_id=user_id)


def _is_last_admin(*, session: Session, member: AgencyMember) -> bool:
    others = session.exec(
        select(func.count())
        .select_from(AgencyMember)
        .where(
            AgencyMember.agency_id == member.agency_id,
            AgencyMember.role == AgencyRole.admin,
            AgencyMember.user_id != member.user_id,
        )
    ).one()
    return others == 0


def _reached(
    *, session: Session, member: AgencyMember, owned: set[uuid.UUID]
) -> set[uuid.UUID]:
    if not owned:
        return set()
    return set(
        session.exec(
            select(WorkspaceMember.company_id).where(
                WorkspaceMember.user_id == member.user_id,
                col(WorkspaceMember.company_id).in_(owned),
            )
        ).all()
    )


def _set_reach(
    *,
    session: Session,
    member: AgencyMember,
    owned: set[uuid.UUID],
    chosen: set[uuid.UUID],
) -> None:
    """Make the person's workspace rows, among this agency's workspaces, exactly
    `chosen`. Rows for other agencies' workspaces are never touched."""
    current = _reached(session=session, member=member, owned=owned)
    drop = current - chosen
    if drop:
        session.execute(
            delete(WorkspaceMember).where(
                col(WorkspaceMember.user_id) == member.user_id,
                col(WorkspaceMember.company_id).in_(drop),
            )
        )
    for company_id in chosen - current:
        session.add(WorkspaceMember(user_id=member.user_id, company_id=company_id))


def has_a_workspace(*, session: Session, user: User) -> bool:
    """Whether the person can open a workspace at sign-in. When the one they had open
    is no longer theirs, another they reach is opened first."""
    _reopen_if_needed(session=session, user_id=user.id)
    session.refresh(user)
    return session.get(WorkspaceMember, (user.id, user.company_id)) is not None


def _reopen_if_needed(*, session: Session, user_id: uuid.UUID) -> None:
    """When the workspace a person has open is no longer theirs, open another one they
    reach. With none left the open one stays as it is: every request is refused, which
    sends them to sign-in, and sign-in tells them why."""
    user = session.get(User, user_id)
    if user is None:
        return
    if session.get(WorkspaceMember, (user.id, user.company_id)) is not None:
        return
    other = session.exec(
        select(WorkspaceMember.company_id)
        .join(Company, col(Company.id) == WorkspaceMember.company_id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(func.lower(Company.name), col(Company.id))
    ).first()
    if other is None:
        return
    user.company_id = other
    session.add(user)
    session.commit()


def agencies_by_id(
    *, session: Session, agency_ids: set[uuid.UUID]
) -> dict[uuid.UUID, Agency]:
    if not agency_ids:
        return {}
    rows = session.exec(select(Agency).where(col(Agency.id).in_(agency_ids))).all()
    return {agency.id: agency for agency in rows}


def admin_names(*, session: Session, agency_id: uuid.UUID) -> str:
    """The agency's Admins as one phrase for a refusal: "Alex Morgan or sam@example.com"."""
    names = [
        u.full_name or u.email for u in admins(session=session, agency_id=agency_id)
    ]
    return " or ".join(names) if names else "an Admin"
