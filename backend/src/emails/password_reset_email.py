"""Password-reset email."""

from src.emails.send import render_html, send_email


def _build_text_body(first_name: str, reset_link: str) -> str:
    lines = [
        f"Password Reset Request",
        "",
        f"Hi {first_name},",
        "",
        "We received a request to reset the password for your SweepStake account.",
        "Click the link below to choose a new password (valid for 30 minutes):",
        "",
        f"  {reset_link}",
        "",
        "If you did not request a password reset, you can safely ignore this email.",
        "Your password will not be changed.",
        "",
        "Best regards,",
        "The SweepStake Team",
        "",
        "---",
        "SweepStake — Football Prediction Competition",
        "You received this email because a password reset was requested for your SweepStake account.",
    ]
    return "\n".join(lines)


async def send_password_reset_email(to_email: str, reset_link: str, first_name: str = "there") -> None:
    context = {"first_name": first_name, "reset_link": reset_link}
    html_body = render_html("password_reset_email.html", context)
    text_body = _build_text_body(first_name, reset_link)
    await send_email(to_email, "Reset your password – SweepStake", html_body, text_body)
