"""
General-purpose email sending primitives.

All specific email functions live in their own modules (e.g. welcome_email.py)
and call render_html / send_email from here.

Test-address interception: if the recipient's domain matches a known test /
local pattern (example.*, local.*, localhost.*, *.example, *.local,
*.localhost) the email is never dispatched.  Instead the HTML body is written
to  data/test_email_{email_name}_{user_id}.html  and the path is logged.

If SMTP is not configured (and the address is not a test address), every send
call is suppressed and the subject + recipient are logged at WARNING level so
the flow is still exercisable locally.
"""

import asyncio
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
# backend/src/emails/send.py → up 4 levels → project root → data/
_DATA_DIR = Path(__file__).resolve().parents[3] / "data"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

_TEST_LABELS = {"example", "local", "localhost"}


def _is_test_address(email: str) -> bool:
    """Return True when the email domain matches a known test/local pattern."""
    try:
        domain = email.lower().split("@", 1)[1]
    except IndexError:
        return False
    parts = domain.split(".")
    # *@example.* / *@local.* / *@localhost.*  (first label is a test name)
    if len(parts) >= 2 and parts[0] in _TEST_LABELS:
        return True
    # *.example / *.local / *.localhost  (TLD is a test name)
    if parts[-1] in _TEST_LABELS:
        return True
    return False


def _save_test_email(to_email: str, html_body: str, user_id: Optional[int]) -> Path:
    """Write the HTML body to disk and return the path."""
    email_name = re.sub(r"[^a-zA-Z0-9._-]", "_", to_email.split("@")[0])
    uid_part = f"_{user_id}" if user_id is not None else ""
    filename = f"test_email_{email_name}{uid_part}.html"
    path = _DATA_DIR / filename
    path.write_text(html_body, encoding="utf-8")
    return path


def render_html(template_name: str, context: dict) -> str:
    """Render a Jinja2 HTML template from the emails/templates directory."""
    return _jinja_env.get_template(template_name).render(**context)


def _smtp_configured() -> bool:
    return bool(settings.smtp_host)


def _send_sync(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    reply_to: Optional[str] = None,
) -> None:
    """Blocking SMTP send — called via asyncio.to_thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.ehlo()
        server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, to_email, msg.as_string())


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    user_id: Optional[int] = None,
    reply_to: Optional[str] = None,
) -> None:
    """
    Dispatch an email asynchronously.

    Test/local addresses are never sent; the HTML body is saved to disk instead.
    When SMTP is unconfigured the send is suppressed with a WARNING log.
    """
    if _is_test_address(to_email):
        try:
            path = _save_test_email(to_email, html_body, user_id)
            logger.warning(
                "Test address detected — email NOT sent to %s | subject: %s | saved to: %s",
                to_email, subject, path,
            )
        except Exception:
            logger.exception("Failed to save test email for %s", to_email)
        return

    if not _smtp_configured():
        logger.warning("SMTP not configured — suppressed email to %s | subject: %s", to_email, subject)
        return

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, html_body, text_body, reply_to)
        logger.info("Email sent to %s | subject: %s", to_email, subject)
    except Exception:
        logger.exception("Failed to send email to %s | subject: %s", to_email, subject)
