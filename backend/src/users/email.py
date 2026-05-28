"""
Email utilities for transactional messages (password reset, etc.).

If SMTP is not configured, the message is logged at WARNING level so the link
is still visible during local development without needing a mail server.
"""

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)


def _smtp_configured() -> bool:
    return bool(settings.email_host)


def _send_sync(to_email: str, subject: str, body_text: str) -> None:
    """Blocking SMTP send — called via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.attach(MIMEText(body_text, "plain"))

    if settings.email_use_ssl:
        ctx = smtplib.SMTP_SSL(settings.email_host, settings.email_port)
    else:
        ctx = smtplib.SMTP(settings.email_host, settings.email_port)

    with ctx as server:
        server.ehlo()
        if not settings.email_use_ssl and settings.email_use_tls:
            server.starttls()
        if settings.email_host_user and settings.email_host_password:
            server.login(settings.email_host_user, settings.email_host_password)
        server.sendmail(settings.email_from, to_email, msg.as_string())


async def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Send a password-reset email.

    Falls back to logging the link if SMTP is not configured — useful for
    local development so you can still test the reset flow without a mail
    server.
    """
    subject = "Reset your password"
    body = (
        f"You requested a password reset.\n\n"
        f"Click the link below to set a new password (valid for 30 minutes):\n\n"
        f"  {reset_link}\n\n"
        f"If you did not request this, you can safely ignore this email.\n"
    )

    if not _smtp_configured():
        logger.warning(
            "SMTP not configured — password reset link for %s: %s",
            to_email,
            reset_link,
        )
        return

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, body)
        logger.info("Password reset email sent to %s", to_email)
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)
        # Do not re-raise: the endpoint returns 200 regardless to avoid leaking
        # whether the address exists.
