"""Delivery for alerts: ntfy push notifications (phone) and/or email.

Settings come from environment variables (e.g. GitHub Actions secrets) or .streamlit/secrets.toml:
  NTFY_TOPIC                    push to https://ntfy.sh/<topic> (install the free ntfy app and subscribe to it)
  SMTP_HOST, SMTP_PORT,
  SMTP_USER, SMTP_PASSWORD,
  ALERT_EMAIL_TO                send an email (e.g. a Gmail app password)
"""

import os
import smtplib
import tomllib
from email.message import EmailMessage
from pathlib import Path

import requests

SECRETS = Path(__file__).with_name(".streamlit") / "secrets.toml"


def setting(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    try:
        value = tomllib.loads(SECRETS.read_text()).get(name)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return None
    return str(value) if value else None


def channels() -> list[str]:
    out = []
    if setting("NTFY_TOPIC"):
        out.append("ntfy")
    if all(setting(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO")):
        out.append("email")
    return out


def send_ntfy(title: str, body: str, priority: int = 3, click: str | None = None) -> None:
    """Publish via ntfy's JSON API, which handles any Unicode in the title (headers can't)."""
    payload = {
        "topic": setting("NTFY_TOPIC"),
        "title": title,
        "message": body,
        "priority": priority,
        "tags": ["chart_with_upwards_trend"],
    }
    if click:
        payload["click"] = click
    resp = requests.post("https://ntfy.sh/", json=payload, timeout=15)
    resp.raise_for_status()


def send_email(title: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = title, setting("SMTP_USER"), setting("ALERT_EMAIL_TO")
    msg.set_content(body)
    with smtplib.SMTP(setting("SMTP_HOST"), int(setting("SMTP_PORT") or 587), timeout=20) as smtp:
        smtp.starttls()
        smtp.login(setting("SMTP_USER"), setting("SMTP_PASSWORD"))
        smtp.send_message(msg)


def send(title: str, body: str, priority: int = 3, click: str | None = None) -> list[str]:
    """Send through every configured channel. Returns the channels used."""
    used = channels()
    if "ntfy" in used:
        send_ntfy(title, body, priority, click)
    if "email" in used:
        send_email(title, body)
    return used
