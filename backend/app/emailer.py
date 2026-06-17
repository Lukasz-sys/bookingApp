import smtplib
from email.message import EmailMessage
from .config import DEV_PRINT_EMAILS, SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USE_TLS, SMTP_USER

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        if DEV_PRINT_EMAILS:
            print("\n--- EMAIL DEV / SMTP NIE SKONFIGUROWANY ---")
            print("TO:", to_email)
            print("SUBJECT:", subject)
            print(body)
            print("--- KONIEC EMAIL DEV ---\n")
        return False
    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    return True
