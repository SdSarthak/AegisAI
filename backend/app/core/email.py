"""
Email notification utility for AegisAI compliance deadline alerts.
Uses Python's smtplib with SSL for secure email delivery.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
) -> bool:
    """
    Send an email using SMTP with SSL.
    Returns True if sent successfully, False otherwise.
    """
    if not settings.SMTP_ENABLED:
        logger.info("SMTP disabled - skipping email to %s: %s", to_email, subject)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info("Email sent to %s: %s", to_email, subject)
        return True

    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False


def build_deadline_alert_email(system_name: str, deadline_date: str, days_remaining: int) -> dict:
    """Build HTML and text email for compliance deadline alerts."""
    subject = f"Compliance Deadline Alert: {system_name} ({days_remaining} days remaining)"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: #e2e8f0; padding: 24px; border-radius: 8px;">
            <h2 style="color: #f59e0b;">Compliance Deadline Alert</h2>
            <p>Your AI system <strong>{system_name}</strong> has a compliance deadline approaching.</p>
            <div style="background: #2d2d44; padding: 16px; border-radius: 6px; margin: 16px 0;">
                <p><strong>Deadline:</strong> {deadline_date}</p>
                <p><strong>Days Remaining:</strong> {days_remaining}</p>
            </div>
            <p>Please log in to AegisAI and complete the required compliance actions before the deadline.</p>
            <a href="#" style="background: #f59e0b; color: #000; padding: 10px 20px;
               border-radius: 4px; text-decoration: none; font-weight: bold;">
               View Compliance Dashboard
            </a>
        </div>
    </body>
    </html>
    """

    text_body = (
        f"Compliance Deadline Alert\n\n"
        f"AI System: {system_name}\n"
        f"Deadline: {deadline_date}\n"
        f"Days Remaining: {days_remaining}\n\n"
        f"Please log in to AegisAI to complete required compliance actions."
    )

    return {"subject": subject, "html_body": html_body, "text_body": text_body}


def build_reassessment_email(system_name: str, expiry_date: str) -> dict:
    """Build HTML and text email for risk reassessment reminders."""
    subject = f"Risk Reassessment Due: {system_name}"

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #1a1a2e; color: #e2e8f0; padding: 24px; border-radius: 8px;">
            <h2 style="color: #6366f1;">Risk Reassessment Reminder</h2>
            <p>The risk assessment for your AI system <strong>{system_name}</strong>
               is expiring soon.</p>
            <div style="background: #2d2d44; padding: 16px; border-radius: 6px; margin: 16px 0;">
                <p><strong>Expiry Date:</strong> {expiry_date}</p>
            </div>
            <p>Please schedule a reassessment to maintain EU AI Act compliance.</p>
            <a href="#" style="background: #6366f1; color: #fff; padding: 10px 20px;
               border-radius: 4px; text-decoration: none; font-weight: bold;">
               Schedule Reassessment
            </a>
        </div>
    </body>
    </html>
    """

    text_body = (
        f"Risk Reassessment Reminder\n\n"
        f"AI System: {system_name}\n"
        f"Assessment Expiry: {expiry_date}\n\n"
        f"Please schedule a reassessment to maintain EU AI Act compliance."
    )

    return {"subject": subject, "html_body": html_body, "text_body": text_body}