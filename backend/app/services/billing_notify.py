"""The emails that tell an agency's Admins about its money: the balance is low, a
payment failed, Connexity is paused.

Each is sent once per stretch of its state: a marker on the agency is set when the
email goes out and emptied when the state ends. They are sent from the scheduled run,
so a state that begins and ends between two runs sends nothing.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlmodel import Session, col

from app.core.config import settings
from app.crud.agency import admins
from app.models.agency import Agency
from app.models.billing import AgencyState
from app.services.billing_state import money_of
from app.utils import (
    EmailData,
    generate_balance_low_email,
    generate_paused_email,
    generate_payment_failed_email,
    send_email,
)

logger = logging.getLogger(__name__)

_PAUSED = (AgencyState.out, AgencyState.unpaid)


def _send(session: Session, agency: Agency, email: EmailData) -> None:
    for admin in admins(session=session, agency_id=agency.id):
        send_email(
            email_to=admin.email, subject=email.subject, html_content=email.html_content
        )


def send_payment_failed(*, session: Session, agency: Agency) -> None:
    """Tell the Admins an automatic payment failed. Called once, when it fails."""
    if not settings.emails_enabled or not settings.public_site_url:
        return
    _send(
        session,
        agency,
        generate_payment_failed_email(
            amount_usd=agency.payment_failed_amount_usd or 0,
            reason=agency.payment_failed_reason or "The payment did not go through.",
        ),
    )


def notify(*, session: Session, agency: Agency) -> str | None:
    """Send what the agency's state calls for, if it was not sent for this stretch.
    Answers `low` or `paused` when an email went out. Commits when a marker changed."""
    money = money_of(session=session, agency=agency)
    can_send = bool(settings.emails_enabled and settings.public_site_url)
    sent: str | None = None
    low = money.state is AgencyState.low and not agency.auto_top_up_enabled
    paused = money.state in _PAUSED
    changed = False

    if low and agency.low_notified_at is None:
        if can_send:
            _send(
                session,
                agency,
                generate_balance_low_email(
                    balance_usd=f"{money.included_left + money.balance:,.2f}",
                    days_left=money.days_left,
                ),
            )
            sent = "low"
        agency.low_notified_at = datetime.now(UTC)
        changed = True
    elif not low and not paused and agency.low_notified_at is not None:
        agency.low_notified_at = None
        changed = True

    if paused and agency.paused_notified_at is None:
        if can_send:
            _send(
                session,
                agency,
                generate_paused_email(unpaid=money.state is AgencyState.unpaid),
            )
            sent = "paused"
        agency.paused_notified_at = datetime.now(UTC)
        changed = True
    elif not paused and agency.paused_notified_at is not None:
        agency.paused_notified_at = None
        changed = True

    if changed:
        session.add(agency)
        session.commit()
    return sent


def run_notifications(*, session: Session) -> dict[str, int]:
    """Every agency that has ever paid. One agency's trouble does not stop the rest."""
    counts: dict[str, int] = {}
    if not settings.billing_enabled:
        return counts
    agencies = session.execute(
        select(Agency).where(col(Agency.first_subscribed_at).is_not(None))
    ).scalars()
    for agency in list(agencies):
        try:
            sent = notify(session=session, agency=agency)
        except Exception:
            session.rollback()
            logger.exception("A billing email could not be worked out")
            continue
        if sent:
            counts[sent] = counts.get(sent, 0) + 1
    return counts
