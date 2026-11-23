import logging
import smtplib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import emails  # type: ignore
from jinja2 import Template

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailData:
    html_content: str
    subject: str


def render_email_template(*, template_name: str, context: dict[str, Any]) -> str:
    template_str = (
        Path(__file__).parent / "email-templates" / "build" / template_name
    ).read_text()
    html_content = Template(template_str).render(context)
    return html_content


SMTP_TIMEOUT_SECONDS = 10
# The logo travels inside the email (an inline attachment the HTML names by `cid:`),
# so it shows whatever the site's address is, also on a deployment nobody outside can
# reach.
LOGO_FILE = "connexity-logo.png"
LOGO_PATH = Path(__file__).parent / "email-templates" / "assets" / LOGO_FILE


def send_email(
    *,
    email_to: str,
    subject: str = "",
    html_content: str = "",
) -> bool:
    """Send one email over SMTP. True when the provider accepted it.

    A refusal or an unreachable provider is logged with the provider's answer and
    returns False; it does not raise, so what the person sees never depends on it.
    """
    assert settings.emails_enabled, "no provided configuration for email variables"
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.EMAILS_FROM_NAME, settings.EMAILS_FROM_EMAIL),
    )
    if f"cid:{LOGO_FILE}" in html_content:
        message.attach(
            filename=LOGO_FILE,
            content_disposition="inline",
            data=LOGO_PATH.read_bytes(),
        )
    smtp_options = {
        "host": settings.SMTP_HOST,
        "port": settings.SMTP_PORT,
        "timeout": SMTP_TIMEOUT_SECONDS,
    }
    if settings.SMTP_TLS:
        smtp_options["tls"] = True
    elif settings.SMTP_SSL:
        smtp_options["ssl"] = True
    if settings.SMTP_USER:
        smtp_options["user"] = settings.SMTP_USER
    if settings.SMTP_PASSWORD:
        smtp_options["password"] = settings.SMTP_PASSWORD
    try:
        response = message.send(to=email_to, smtp=smtp_options)
    except (OSError, smtplib.SMTPException) as exc:
        logger.warning("Email not sent (%s): %s", subject, exc)
        return False
    if response.status_code != 250:
        logger.warning(
            "Email not sent (%s): status %s, %s",
            subject,
            response.status_code,
            response.error or response.status_text,
        )
        return False
    logger.info("Email sent (%s)", subject)
    return True


def generate_test_email(email_to: str) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - Test email"
    html_content = render_email_template(
        template_name="test_email.html",
        context={"project_name": settings.PROJECT_NAME, "email": email_to},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_new_account_email(
    email_to: str, username: str, password: str
) -> EmailData:
    project_name = settings.PROJECT_NAME
    subject = f"{project_name} - New account for user {username}"
    html_content = render_email_template(
        template_name="new_account.html",
        context={
            "project_name": settings.PROJECT_NAME,
            "username": username,
            "password": password,
            "email": email_to,
            "link": settings.public_site_url,
        },
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_reset_password_email(*, token: str) -> EmailData:
    """The email with the single-use link (design: Connexity Email, `reset`)."""
    subject = "Reset your Connexity password"
    site_url = settings.public_site_url
    html_content = render_email_template(
        template_name="reset_password.html",
        context={"subject": subject, "link": f"{site_url}/reset/{token}"},
    )
    return EmailData(html_content=html_content, subject=subject)


def generate_google_sign_in_email() -> EmailData:
    """For an account that signs in only with Google and has no password to reset
    (design: Connexity Email, `google`)."""
    subject = "Signing in to Connexity"
    site_url = settings.public_site_url
    html_content = render_email_template(
        template_name="google_sign_in.html",
        context={"subject": subject, "link": f"{site_url}/login"},
    )
    return EmailData(html_content=html_content, subject=subject)


is_prod = settings.ENVIRONMENT == "production"
