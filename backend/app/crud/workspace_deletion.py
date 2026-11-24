"""Deleting a workspace's data, for good.

A deletion removes everything Connexity holds about the workspace: calls with their
transcripts, tool calls and findings, issues, specs, scenarios, test runs, decision
records, connections and tokens. Three kinds of row stay, with no call content:

- usage rows, which invoices need, with their links to calls and runs emptied;
- the workspace's own row and each agent's row, reduced to id and name, so the usage
  rows still say whose usage it was;
- the deletion's record in the agency (`workspace_deletion`).

The deletion runs table by table and commits after each, in an order that can be run
again: a failed run is continued by "Try again". Connexity stores no audio, only the
voice platform's link to a recording, so there is nothing to remove outside the
database. Nothing is called on the voice platform, n8n or a CRM.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col

from app.crud.agency import _reopen_if_needed, agency_workspaces
from app.models.agency import Agency, AgencyMember, AgencyRole
from app.models.agent import Agent
from app.models.call import Call
from app.models.check import Issue
from app.models.company import Company
from app.models.integration import Integration
from app.models.usage import UsageRecord
from app.models.user import User
from app.models.workspace_deletion import DeletionState, WorkspaceDeletion
from app.models.workspace_member import WorkspaceMember

logger = logging.getLogger(__name__)

# Tables with a `company_id` that a deletion does not empty. Every other table with one
# is emptied for the workspace; `test_workspace_deletion.py` fails when a new table
# with workspace data would be missed.
KEPT_TABLES = frozenset(
    {
        "user",  # a person's open workspace; people are not deleted
        "usage_record",  # invoices
        "agent",  # reduced to id and name
        "workspace_deletion",  # the record of the deletion itself
    }
)


# A deletion runs inside one request. One still marked as running after this long
# belongs to a request that died, and can be continued like a failed one.
STALLED_AFTER = timedelta(minutes=5)


def shown_state(deletion: WorkspaceDeletion) -> DeletionState:
    """The deletion's state as people see it: a run that died midway counts as failed,
    so it can be tried again."""
    started = deletion.created_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    if (
        deletion.state is DeletionState.deleting
        and datetime.now(UTC) - started > STALLED_AFTER
    ):
        return DeletionState.failed
    return deletion.state


class LastWorkspaceError(Exception):
    """An agency keeps at least one workspace."""


class DeletionRunningError(Exception):
    """The workspace is already deleted or being deleted."""


@dataclass(frozen=True)
class Counts:
    calls: int
    agents: int
    issues: int


def _count(session: Session, model: type[SQLModel], company_id: uuid.UUID) -> int:
    table = model.__table__  # type: ignore[attr-defined]
    return session.execute(
        select(func.count()).select_from(table).where(table.c.company_id == company_id)
    ).scalar_one()


def counts(*, session: Session, company_id: uuid.UUID) -> Counts:
    return Counts(
        calls=_count(session, Call, company_id),
        agents=_count(session, Agent, company_id),
        issues=_count(session, Issue, company_id),
    )


def connection_names(*, session: Session, company_id: uuid.UUID) -> list[str]:
    """The platforms the workspace is connected to, each once, by name."""
    providers = session.execute(
        select(Integration.provider)
        .where(col(Integration.company_id) == company_id)
        .distinct()
    ).scalars()
    return sorted({str(getattr(p, "value", p)) for p in providers})


def can_delete(*, session: Session, user: User, agency_id: uuid.UUID) -> bool:
    """Deleting is for an Admin of the agency who can approve."""
    member = session.get(AgencyMember, (agency_id, user.id))
    return member is not None and member.role == AgencyRole.admin and member.can_approve


def who_can_delete(*, session: Session, agency_id: uuid.UUID) -> str:
    """The people who can delete, as one phrase for a refusal."""
    people = session.execute(
        select(User)
        .join(AgencyMember, col(AgencyMember.user_id) == User.id)
        .where(
            col(AgencyMember.agency_id) == agency_id,
            col(AgencyMember.role) == AgencyRole.admin,
            col(AgencyMember.can_approve).is_(True),
        )
        .order_by(func.lower(User.email))
    ).scalars()
    names = [u.full_name or u.email for u in people]
    return " or ".join(names) if names else "an Admin who can approve"


def deletions(*, session: Session, agency_id: uuid.UUID) -> list[WorkspaceDeletion]:
    """The agency's record of deleted workspaces, newest first."""
    return list(
        session.execute(
            select(WorkspaceDeletion)
            .where(col(WorkspaceDeletion.agency_id) == agency_id)
            .order_by(col(WorkspaceDeletion.created_at).desc())
        ).scalars()
    )


def get_deletion(
    *, session: Session, agency_id: uuid.UUID, company_id: uuid.UUID
) -> WorkspaceDeletion | None:
    return session.execute(
        select(WorkspaceDeletion).where(
            col(WorkspaceDeletion.agency_id) == agency_id,
            col(WorkspaceDeletion.company_id) == company_id,
        )
    ).scalar_one_or_none()


def start_deletion(
    *, session: Session, agency: Agency, workspace: Company, deleted_by: User
) -> WorkspaceDeletion:
    """Take the workspace away from everyone and delete its data. Commits.

    From the first commit nobody reaches the workspace, on the web or through an
    assistant, whatever happens to the rest of the run.

    Raises:
        LastWorkspaceError: it is the agency's only workspace.
        DeletionRunningError: it is already deleted or being deleted.
    """
    if workspace.deleted_at is not None:
        raise DeletionRunningError
    remaining = agency_workspaces(session=session, agency_id=agency.id)
    if len(remaining) <= 1:
        raise LastWorkspaceError
    held = counts(session=session, company_id=workspace.id)
    deletion = WorkspaceDeletion(
        agency_id=agency.id,
        company_id=workspace.id,
        workspace_name=workspace.name,
        deleted_by_user_id=deleted_by.id,
        deleted_by_name=deleted_by.full_name or deleted_by.email,
        calls=held.calls,
        agents=held.agents,
        issues=held.issues,
    )
    session.add(deletion)
    workspace.deleted_at = datetime.now(UTC)
    session.add(workspace)
    had_it_open = list(
        session.execute(
            select(User.id).where(col(User.company_id) == workspace.id)
        ).scalars()
    )
    session.execute(
        delete(WorkspaceMember).where(col(WorkspaceMember.company_id) == workspace.id)
    )
    # Unlinked in this same commit: the webhook and the call pull find an agent by its
    # connection, so no new call is stored even if a later step fails.
    session.execute(
        update(Agent)
        .where(col(Agent.company_id) == workspace.id)
        .values(integration_id=None, platform_agent_id=None)
    )
    try:
        session.commit()
    except IntegrityError as exc:
        # Another request started deleting this workspace a moment earlier.
        session.rollback()
        raise DeletionRunningError from exc
    for user_id in had_it_open:
        _reopen_if_needed(session=session, user_id=user_id)
    session.refresh(deletion)
    return run_deletion(session=session, deletion=deletion)


def run_deletion(*, session: Session, deletion: WorkspaceDeletion) -> WorkspaceDeletion:
    """Remove the workspace's data, or continue a run that failed. Commits after each
    step. A step that breaks leaves the deletion `failed`, with the step named."""
    company_id = deletion.company_id
    deletion_id = deletion.id
    step = "start"
    try:
        deletion.state = DeletionState.deleting
        deletion.error = None
        session.add(deletion)
        session.commit()

        step = "usage_record"
        session.execute(
            update(UsageRecord)
            .where(col(UsageRecord.company_id) == company_id)
            .values(call_id=None, test_case_result_id=None, run_id=None)
        )
        step = "agent"
        session.execute(
            update(Agent)
            .where(col(Agent.company_id) == company_id)
            .values(
                description=None,
                platform=None,
                integration_id=None,
                platform_agent_id=None,
                platform_agent_name=None,
                agent_metadata=None,
                created_by=None,
                calls_last_synced_at=None,
                scan_from=None,
                scan_until=None,
                scan_total=None,
                scan_cursor=None,
                deleted_at=func.now(),
            )
        )
        # An assistant connected while this workspace was open stays connected, now on
        # the workspace its person has open. One whose person reaches no other
        # workspace is removed with the rest below.
        step = "oauth_refresh_token"
        session.execute(
            text(
                "UPDATE oauth_refresh_token AS t SET company_id = u.company_id "
                'FROM "user" AS u WHERE t.user_id = u.id '
                "AND t.company_id = :company_id AND u.company_id <> :company_id"
            ),
            {"company_id": company_id},
        )
        session.commit()

        # Children before parents, so no row is left pointing at a removed one.
        for table in reversed(SQLModel.metadata.sorted_tables):
            if "company_id" not in table.c or table.name in KEPT_TABLES:
                continue
            step = table.name
            session.execute(delete(table).where(table.c.company_id == company_id))
            session.commit()

        step = "finish"
        deletion = session.get(WorkspaceDeletion, deletion_id) or deletion
        deletion.state = DeletionState.done
        deletion.finished_at = datetime.now(UTC)
        session.add(deletion)
        session.commit()
    except Exception as exc:  # any failure must leave a record that can be retried
        session.rollback()
        # The step and the kind of error only: an error's text can quote a row.
        logger.exception("Deleting a workspace's data failed at step %s", step)
        deletion = session.get(WorkspaceDeletion, deletion_id) or deletion
        deletion.state = DeletionState.failed
        deletion.error = f"{step}: {type(exc).__name__}"[:255]
        session.add(deletion)
        session.commit()
    session.refresh(deletion)
    return deletion
