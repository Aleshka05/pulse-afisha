# app/services/email.py
import os
import smtplib
from email.message import EmailMessage
from typing import Optional


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_email(
    to: str,
    subject: str,
    text: str,
    *,
    reply_to: Optional[str] = None,
) -> None:
    """
    Простейшая синхронная отправка письма через SMTP (Gmail).

    В проде можно вынести в фоновые задачи, но для нашего проекта так норм.
    """
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASSWORD):
        # Ничего не отправляем, если не настроено – чтобы не падало.
        print("[send_email] SMTP не настроен, письмо не отправлено")
        return

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
