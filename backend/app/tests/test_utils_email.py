from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.utils import (
    generate_new_account_email,
    generate_test_email,
    render_email_template,
    send_email,
)


def test_render_email_template_renders_context_values() -> None:
    html = render_email_template(
        template_name="test_email.html",
        context={"project_name": "Connexity", "email": "person@example.com"},
    )

    assert "Connexity" in html
    assert "person@example.com" in html


def test_generate_test_email_builds_subject_and_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "PROJECT_NAME", "Connexity")

    email_data = generate_test_email("person@example.com")

    assert email_data.subject == "Connexity - Test email"
    assert "person@example.com" in email_data.html_content
    assert "Connexity" in email_data.html_content


def test_generate_new_account_email_builds_subject_and_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "PROJECT_NAME", "Connexity")
    monkeypatch.setattr(settings, "SITE_URL", "https://app.example.com")

    email_data = generate_new_account_email(
        "person@example.com", "new-user", "secret-pass"
    )

    assert email_data.subject == "Connexity - New account for user new-user"
    assert "new-user" in email_data.html_content
    assert "secret-pass" in email_data.html_content
    assert "https://app.example.com" in email_data.html_content


def test_send_email_builds_tls_and_auth_smtp_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_TLS", True)
    monkeypatch.setattr(settings, "SMTP_SSL", False)
    monkeypatch.setattr(settings, "SMTP_USER", "smtp-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp-password")
    monkeypatch.setattr(settings, "EMAILS_FROM_NAME", "Connexity")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")

    message = MagicMock()
    with patch("app.utils.emails.Message", return_value=message) as message_cls:
        send_email(
            email_to="person@example.com",
            subject="subject",
            html_content="<p>hello</p>",
        )

    message_cls.assert_called_once_with(
        subject="subject",
        html="<p>hello</p>",
        mail_from=("Connexity", "no-reply@example.com"),
    )
    message.send.assert_called_once_with(
        to="person@example.com",
        smtp={
            "host": "smtp.example.com",
            "port": 587,
            "tls": True,
            "user": "smtp-user",
            "password": "smtp-password",
        },
    )


def test_send_email_builds_ssl_smtp_options_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 465)
    monkeypatch.setattr(settings, "SMTP_TLS", False)
    monkeypatch.setattr(settings, "SMTP_SSL", True)
    monkeypatch.setattr(settings, "SMTP_USER", None)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", None)
    monkeypatch.setattr(settings, "EMAILS_FROM_NAME", "Connexity")
    monkeypatch.setattr(settings, "EMAILS_FROM_EMAIL", "no-reply@example.com")

    message = MagicMock()
    with patch("app.utils.emails.Message", return_value=message):
        send_email(
            email_to="person@example.com",
            subject="subject",
            html_content="<p>hello</p>",
        )

    message.send.assert_called_once_with(
        to="person@example.com",
        smtp={"host": "smtp.example.com", "port": 465, "ssl": True},
    )


def test_send_email_requires_email_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SMTP_HOST", None)

    with pytest.raises(
        AssertionError, match="no provided configuration for email variables"
    ):
        send_email(
            email_to="person@example.com",
            subject="subject",
            html_content="<p>hello</p>",
        )
