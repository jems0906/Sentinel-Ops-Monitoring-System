import smtplib
from email.message import EmailMessage

from app.config import settings


def send_email_alert(subject: str, body: str) -> bool:
    if not settings.smtp_host or not settings.alert_to_email:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.alert_from_email
    msg["To"] = settings.alert_to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        if settings.smtp_username and settings.smtp_password:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)

    return True
