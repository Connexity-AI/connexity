import uuid
from typing import Any

from sqlmodel import Session, col, func, select

from app.core.security import get_password_hash, verify_password
from app.crud.agency import new_agency
from app.models import User, UserCreate, UserUpdate
from app.models.agency import AgencyMember, AgencyRole
from app.models.company import Company, workspace_name_from_email
from app.models.user import AuthProvider
from app.models.workspace_member import WorkspaceMember


def create_user(
    *,
    session: Session,
    user_create: UserCreate,
    company_id: uuid.UUID | None = None,
) -> User:
    """Create a user and, when no company_id is given, their own agency and first
    workspace, with them as the agency's Admin.

    Pass an explicit ``company_id`` only when adding a user to an existing workspace
    (e.g. from a manual admin script); they join its agency as a Member who reaches
    that workspace.
    """
    agency_id: uuid.UUID | None = None
    if company_id is None:
        company_id, agency_id = _create_first_workspace(
            session=session, email=user_create.email
        )
    db_obj = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "company_id": company_id,
        },
    )
    session.add(db_obj)
    session.flush()
    _join(session=session, user=db_obj, company_id=company_id, own_agency=agency_id)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_google_user(*, session: Session, email: str, full_name: str | None) -> User:
    """An account made by signing in with Google: no password, its own agency and a
    first workspace, both named from the email domain."""
    company_id, agency_id = _create_first_workspace(session=session, email=email)
    db_obj = User(
        email=email,
        full_name=full_name,
        provider=AuthProvider.google,
        hashed_password=None,
        company_id=company_id,
    )
    session.add(db_obj)
    session.flush()
    _join(session=session, user=db_obj, company_id=company_id, own_agency=agency_id)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def _create_first_workspace(
    *, session: Session, email: str
) -> tuple[uuid.UUID, uuid.UUID]:
    """A new person's agency and first workspace, as (workspace, agency)."""
    agency = new_agency(session=session, email=email)
    company = Company(name=workspace_name_from_email(email), agency_id=agency.id)
    session.add(company)
    session.flush()
    return company.id, agency.id


def _join(
    *,
    session: Session,
    user: User,
    company_id: uuid.UUID,
    own_agency: uuid.UUID | None,
) -> None:
    """Put a new person in their workspace and its agency: Admin of an agency made
    for them, a Member with that one workspace otherwise."""
    session.add(WorkspaceMember(user_id=user.id, company_id=company_id))
    if own_agency is not None:
        session.add(
            AgencyMember(agency_id=own_agency, user_id=user.id, role=AgencyRole.admin)
        )
        return
    company = session.get(Company, company_id)
    if company is None:
        return
    session.add(
        AgencyMember(
            agency_id=company.agency_id,
            user_id=user.id,
            role=AgencyRole.member,
            all_workspaces=False,
        )
    )


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def find_user_by_email_ignoring_case(*, session: Session, email: str) -> User | None:
    """For sign-in from an identity provider, which may change an email's case."""
    return session.exec(
        select(User).where(func.lower(User.email) == email.strip().lower())
    ).first()


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def list_users_by_ids(
    *,
    session: Session,
    user_ids: list[uuid.UUID],
    company_id: uuid.UUID | None = None,
) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}
    statement = select(User).where(col(User.id).in_(user_ids))
    if company_id is not None:
        statement = statement.where(User.company_id == company_id)
    rows = list(session.exec(statement).all())
    return {u.id: u for u in rows}


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not db_user.hashed_password or not verify_password(
        password, db_user.hashed_password
    ):
        return None
    return db_user
