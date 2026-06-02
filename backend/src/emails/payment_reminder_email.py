"""Payment reminder email sent to participants who have not yet paid their stake."""

import re
from typing import Optional

from markupsafe import Markup, escape

from src.config import settings
from src.emails.send import render_html, send_email

_URL_RE = re.compile(r'((?:https?://|www\.)[^\s<>"\']+)', re.IGNORECASE)


def _linkify_stake(stake: str) -> Markup:
    """HTML-escape stake text, turn URLs into <a> links, convert newlines to <br>."""
    escaped = str(escape(stake))

    def _make_link(m: re.Match) -> str:
        url = m.group(1).rstrip(".,;:!?)")
        href = url if url.lower().startswith(("http://", "https://")) else f"http://{url}"
        return f'<a href="{href}" style="color:#2563eb;text-decoration:underline;">{url}</a>'

    linked = _URL_RE.sub(_make_link, escaped)
    return Markup(linked.replace("\n", "<br>"))


async def send_payment_reminder_email(
    to_email: str,
    first_name: str,
    tournament_name: str,
    tournament_id: int,
    stake: str,
    admin: Optional[dict] = None,
    all_admins: Optional[list[dict]] = None,
    user_id: Optional[int] = None,
) -> None:
    admin = admin or {}
    tournament_url = f"{settings.main_host.rstrip('/')}/tournament/{tournament_id}"

    sign_off = admin.get("first_name") or "The Organiser"
    full_name = sign_off + (f" {admin['last_name']}" if admin.get("last_name") else "")
    reply_to = f"{full_name} <{admin['email']}>" if admin.get("email") else None

    footer_admins = all_admins or ([admin] if admin.get("first_name") else [])
    admin_footer = [
        {
            "full_name": a.get("first_name", "") + (f" {a['last_name']}" if a.get("last_name") else ""),
            "email": a.get("email", ""),
        }
        for a in footer_admins
        if a.get("first_name")
    ]

    context = {
        "first_name": first_name,
        "tournament_name": tournament_name,
        "tournament_url": tournament_url,
        "stake": _linkify_stake(stake),
        "admin_sign_off": sign_off,
        "admin_footer": admin_footer,
    }
    html_body = render_html("payment_reminder_email.html", context)
    text_body = (
        f"Hi {first_name}, this is a payment reminder for the {tournament_name} SweepStake. "
        f"Please view this email in an HTML-capable client. Go to: {tournament_url}"
    )
    await send_email(
        to_email,
        f"Stake Payment Reminder: {tournament_name} – SweepStake",
        html_body,
        text_body,
        user_id=user_id,
        reply_to=reply_to,
    )
