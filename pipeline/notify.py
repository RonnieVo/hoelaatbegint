"""Mail naar de eigenaar. Gebruikt SMTP (bijv. het mailadres van je eigen domein of Gmail met app-wachtwoord).

Omgevingsvariabelen: SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASS, MAIL_TO.
Zonder instellingen wordt de mail alleen in de log getoond.
"""
import os
import smtplib
from email.message import EmailMessage


def send_mail(subject, body):
    if not os.environ.get("SMTP_HOST"):
        print(f"[mail niet ingesteld] {subject}\n{body}")
        return
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, os.environ["SMTP_USER"], os.environ["MAIL_TO"]
    msg.set_content(body)
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)
