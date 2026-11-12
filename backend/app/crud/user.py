import uuid
from typing import Any

from sqlmodel import Session, col, func, select

from app.core.security import get_password_hash, verify_password
from app.models import User, UserCreate, UserUpdate
from app.models.company import Company, workspace_name_from_email
from app.models.custom_metric import CustomMetric
from app.models.user import AuthProvider
from app.models.workspace_member import WorkspaceMember


def _seed_predefined_metrics_for_company(
    *, session: Session, company_id: uuid.UUID
) -> None:
    """Copy the predefined system metrics into a freshly-created company.

    Each tenant gets its own row per built-in metric so toggling ``is_draft``
    only affects that tenant. The rows keep ``is_predefined=True`` so the UI
    can still label them "Built-in", but visibility is scoped by company.
    """
    from app.services.predefined_metrics import PREDEFINED_METRICS

    existing_names = set(
        session.exec(
            select(CustomMetric.name).where(
                CustomMetric.company_id == company_id,
                col(CustomMetric.deleted_at).is_(None),
            )
        ).all()
    )
    for definition in PREDEFINED_METRICS:
        if definition.name in existing_names:
            continue
        session.add(
            CustomMetric(
                name=definition.name,
                display_name=definition.display_name,
                description=definition.description,
                tier=definition.tier,
                default_weight=definition.default_weight,
                score_type=definition.score_type,
                rubric=definition.rubric,
                include_in_defaults=definition.include_in_defaults,
                is_predefined=True,
                is_draft=False,
                company_id=company_id,
                created_by=None,
            )
        )


def create_user(
    *,
    session: Session,
    user_create: UserCreate,
    company_id: uuid.UUID | None = None,
) -> User:
    """Create a user and, when no company_id is given, a fresh Company for them.

    Multi-tenancy: every signup gets its own private Company plus a per-tenant
    copy of every built-in (predefined) metric. Pass an explicit ``company_id``
    only when adding a user to an existing company (e.g. from a manual admin
    script); in that case no metric seeding happens.
    """
    if company_id is None:
        company_id = _create_first_workspace(session=session, email=user_create.email)
    db_obj = User.model_validate(
        user_create,
        update={
            "hashed_password": get_password_hash(user_create.password),
            "company_id": company_id,
        },
    )
    session.add(db_obj)
    session.flush()
    session.add(WorkspaceMember(user_id=db_obj.id, company_id=company_id))
    session.commit()
    session.refresh(db_obj)
    return db_obj


def create_google_user(*, session: Session, email: str, full_name: str | None) -> User:
    """An account made by signing in with Google: no password, its first workspace
    named from the email domain."""
    company_id = _create_first_workspace(session=session, email=email)
    db_obj = User(
        email=email,
        full_name=full_name,
        provider=AuthProvider.google,
        hashed_password=None,
        company_id=company_id,
    )
    session.add(db_obj)
    session.flush()
    session.add(WorkspaceMember(user_id=db_obj.id, company_id=company_id))
    session.commit()
    session.refresh(db_obj)
    return db_obj


def _create_first_workspace(*, session: Session, email: str) -> uuid.UUID:
    """A new person's first workspace, with its copy of the built-in metrics."""
    company = Company(name=workspace_name_from_email(email))
    session.add(company)
    session.flush()
    _seed_predefined_metrics_for_company(session=session, company_id=company.id)
    return company.id


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
