"""What assistants report about Connexity itself (`send_feedback`): each report is
stored first, then posted to the team's Notion database, and retried on the scheduled
call pull until it gets there or runs out of tries
(`plans/2026-11-19-assistant-feedback.md`).

A report never fails because Notion is down, and without the Notion settings (local
runs, self-hosting) reports are only stored.
"""

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.crud.feedback import claim_report, reports_since, unsent_reports
from app.models.company import Company
from app.models.enums import FeedbackKind
from app.models.feedback import FeedbackReport
from app.models.user import User

logger = logging.getLogger(__name__)

# Reports one workspace may send in a day (Dmytro, 2026-11-19).
DAILY_CAP = 20
# Tries to reach Notion per report, then it stays stored (Dmytro, 2026-11-19).
MAX_TRIES = 5
# Reports posted on one tick of the scheduled pull, so a Notion outage cannot hold it.
POSTS_PER_TICK = 10
# A post that started this long ago and never finished may be tried again.
CLAIM_STALE = timedelta(minutes=2)
# An error is kept up to this many characters; longer is cut, not refused.
ERROR_KEPT = 10_000
# Notion takes at most this many characters in one text value.
NOTION_TEXT = 2000
_NOTION_URL = "https://api.notion.com/v1/pages"
_NOTION_VERSION = "2022-06-28"
_TIMEOUT_SECONDS = 10.0

# Reports being posted in this process, kept so they are not collected mid-way.
_POSTING: set[asyncio.Task[None]] = set()


class FeedbackRefused(Exception):
    """Nothing was stored, and why."""


@dataclass(frozen=True)
class FeedbackIn:
    kind: FeedbackKind
    title: str
    what_happened: str | None
    wanted: str | None
    tool: str | None
    error: str | None
    ids: list[str]
    assistant_name: str | None
    session_name: str | None


def connexity_version() -> str:
    """The running revision on Cloud Run, or "local"."""
    return os.environ.get("K_REVISION") or "local"


def notion_configured() -> bool:
    return bool(settings.NOTION_FEEDBACK_TOKEN and settings.NOTION_FEEDBACK_DATABASE_ID)


def _clean(text: str | None) -> str | None:
    value = (text or "").strip()
    return value or None


def store_report(
    *, session: Session, company_id: uuid.UUID, person: User, report: FeedbackIn
) -> FeedbackReport:
    """Store one report.

    Raises:
        FeedbackRefused: it is missing what it needs, or the workspace sent its
            reports for today.
    """
    title = _clean(report.title)
    if title is None:
        msg = "A report needs a title: one line saying what is wrong or missing."
        raise FeedbackRefused(msg)
    what_happened, wanted = _clean(report.what_happened), _clean(report.wanted)
    if report.kind is FeedbackKind.BUG and what_happened is None:
        msg = (
            "A bug needs `what_happened`: what you did, which tool, what you "
            "expected and what came back."
        )
        raise FeedbackRefused(msg)
    if report.kind is FeedbackKind.FEATURE_REQUEST and wanted is None:
        msg = "A feature request needs `wanted`: what the work needed and could not do."
        raise FeedbackRefused(msg)
    since = datetime.now(UTC) - timedelta(days=1)
    if reports_since(session=session, company_id=company_id, since=since) >= DAILY_CAP:
        msg = (
            f"This workspace sent {DAILY_CAP} reports in the last 24 hours, the most it "
            "can. Nothing was stored; send it later."
        )
        raise FeedbackRefused(msg)
    stored = FeedbackReport(
        company_id=company_id,
        kind=report.kind,
        title=title[:200],
        what_happened=what_happened,
        wanted=wanted,
        tool=(tool[:100] if (tool := _clean(report.tool)) else None),
        error=(error[:ERROR_KEPT] if (error := _clean(report.error)) else None),
        ids=[i.strip()[:100] for i in report.ids if i.strip()][:50] or None,
        sent_by=person.id,
        assistant_name=report.assistant_name,
        session_name=report.session_name,
        connexity_version=connexity_version()[:100],
    )
    session.add(stored)
    session.commit()
    session.refresh(stored)
    return stored


def _text(value: str | None) -> dict[str, Any]:
    content = (value or "")[:NOTION_TEXT]
    return {"rich_text": [{"text": {"content": content}}] if content else []}


def notion_properties(
    report: FeedbackReport, workspace: str, sent_by: str
) -> dict[str, Any]:
    """The report as a row of the "Assistant feedback" database."""
    assistant = " · ".join(
        part for part in (report.assistant_name, report.session_name) if part
    )
    return {
        "Title": {"title": [{"text": {"content": report.title[:NOTION_TEXT]}}]},
        "Kind": {
            "select": {
                "name": "Bug" if report.kind is FeedbackKind.BUG else "Feature request"
            }
        },
        "Status": {"status": {"name": "New"}},
        "What happened": _text(report.what_happened),
        "Wanted": _text(report.wanted),
        "Tool": _text(report.tool),
        "Error": _text(report.error),
        "IDs": _text(", ".join(report.ids or [])),
        "Workspace": _text(workspace),
        "Sent by": _text(sent_by),
        "Assistant": _text(assistant),
        "Connexity version": _text(report.connexity_version),
        "Report ID": _text(str(report.id)),
        "Received": {"date": {"start": report.received_at.isoformat()}},
    }


async def _post(report: FeedbackReport, workspace: str, sent_by: str) -> str:
    """Post one report; its Notion page id.

    Raises:
        RuntimeError: Notion refused it, timed out or answered nonsense.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                _NOTION_URL,
                headers={
                    "Authorization": f"Bearer {settings.NOTION_FEEDBACK_TOKEN}",
                    "Notion-Version": _NOTION_VERSION,
                },
                json={
                    "parent": {"database_id": settings.NOTION_FEEDBACK_DATABASE_ID},
                    "properties": notion_properties(report, workspace, sent_by),
                },
                timeout=_TIMEOUT_SECONDS,
            )
    except httpx.HTTPError as exc:
        msg = f"Could not reach Notion: {type(exc).__name__}"
        raise RuntimeError(msg) from exc
    if response.status_code != 200:
        msg = f"Notion answered {response.status_code}: {response.text[:300]}"
        raise RuntimeError(msg)
    try:
        page_id = response.json().get("id")
    except ValueError as exc:
        msg = "Notion did not answer JSON"
        raise RuntimeError(msg) from exc
    if not isinstance(page_id, str) or not page_id:
        msg = "Notion answered without a page id"
        raise RuntimeError(msg)
    return page_id


async def post_report(session: Session, report: FeedbackReport) -> bool:
    """One try at posting ``report`` to Notion; whether it got there. Never raises."""
    if not notion_configured() or report.notion_page_id:
        return False
    now = datetime.now(UTC)
    if not claim_report(
        session=session,
        report_id=report.id,
        now=now,
        stale_before=now - CLAIM_STALE,
    ):
        return False
    session.refresh(report)
    company = session.get(Company, report.company_id)
    person = session.get(User, report.sent_by) if report.sent_by else None
    try:
        page_id = await _post(
            report,
            company.name if company else str(report.company_id),
            (person.full_name or person.email) if person else "",
        )
    except RuntimeError as exc:
        logger.warning("Feedback report %s did not reach Notion: %s", report.id, exc)
        report.last_error = str(exc)[:500]
        report.claimed_at = None
        session.add(report)
        session.commit()
        return False
    report.notion_page_id = page_id[:64]
    report.posted_at = datetime.now(UTC)
    report.last_error = None
    session.add(report)
    session.commit()
    return True


async def _post_by_id(report_id: uuid.UUID) -> None:
    with Session(engine) as session:
        report = session.get(FeedbackReport, report_id)
        if report is not None:
            await post_report(session, report)


def post_in_background(report_id: uuid.UUID) -> None:
    """Post a stored report without making the assistant wait for Notion."""
    if not notion_configured():
        return
    task = asyncio.get_running_loop().create_task(_post_by_id(report_id))
    _POSTING.add(task)
    task.add_done_callback(_POSTING.discard)


async def post_unsent(*, session: Session) -> int:
    """Retry every stored report not yet in Notion with tries left; how many got
    there. Called on each scheduled call pull."""
    if not notion_configured():
        return 0
    sent = 0
    for report in unsent_reports(
        session=session, max_tries=MAX_TRIES, limit=POSTS_PER_TICK
    ):
        if await post_report(session, report):
            sent += 1
    return sent
