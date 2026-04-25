import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from core.runtime_config import load_smtp_config


def _logs_dir() -> Path:
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _smtp_settings():
    settings = load_smtp_config()
    if not settings.get("host"):
        settings["host"] = os.getenv("BOMAKSAN_SMTP_HOST", "").strip()
    if not settings.get("username"):
        settings["username"] = os.getenv("BOMAKSAN_SMTP_USER", "").strip()
    if not settings.get("password"):
        settings["password"] = os.getenv("BOMAKSAN_SMTP_PASSWORD", "").strip()
    if not settings.get("from_email"):
        settings["from_email"] = os.getenv("BOMAKSAN_SMTP_FROM", "").strip()
    return settings


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None):
    settings = _smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        log_path = _logs_dir() / "email_verification.log"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                f"[{datetime.now().isoformat()}]\nTO: {to_email}\nSUBJECT: {subject}\n{body}\n{'-' * 60}\n"
            )
        return {
            "status": "logged",
            "message": f"SMTP ayari bulunamadi. E-posta icerigi {log_path} dosyasina yazildi.",
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("Bomaksan Maliyet Analizleri", settings["from_email"]))
    message["To"] = to_email
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings["host"], settings["port"], timeout=30) as smtp:
        smtp.ehlo()
        if settings["use_tls"]:
            smtp.starttls()
            smtp.ehlo()
        if settings["username"]:
            smtp.login(settings["username"], settings["password"])
        smtp.send_message(message)

    return {
        "status": "sent",
        "message": f"E-posta {to_email} adresine gönderildi.",
    }
