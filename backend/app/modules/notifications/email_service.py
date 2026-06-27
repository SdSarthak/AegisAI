import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_email(to: str, subject: str, html_body: str):
    if not settings.SMTP_HOST:
        logger.warning("SMTP not configured — skipping email")
        return

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = settings.SMTP_FROM
    msg['To'] = to

    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)
        logger.info(f"Email sent successfully to {to}")
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")

def build_notification_email(user_name: str, notification: dict) -> str:
    """Builds an HTML email template for a single notification."""
    return f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 24px;">
            <h1 style="color: #6366f1; font-size: 20px;">AegisAI</h1>
            <p style="color: #64748b;">AI Governance, Risk & Compliance</p>
        </div>
        <div style="background: #f8fafc; border-radius: 12px; padding: 24px;">
            <p style="color: #475569;">Hi {user_name},</p>
            <h2 style="font-size: 18px; margin: 16px 0;">{notification.get('title', 'New Alert')}</h2>
            <p style="color: #64748b; line-height: 1.6;">{notification.get('message', '')}</p>
            <a href="{settings.APP_URL}/notifications"
               style="display: inline-block; margin-top: 16px; padding: 10px 24px;
                      background: #6366f1; color: white; text-decoration: none;
                      border-radius: 8px; font-weight: 500;">
                View in AegisAI
            </a>
        </div>
        <div style="text-align: center; margin-top: 24px; font-size: 12px; color: #94a3b8;">
            <a href="{settings.APP_URL}/settings/notifications" style="color: #6366f1;">Manage notifications</a>
            &middot;
            <a href="{settings.APP_URL}/unsubscribe?token={notification.get('unsubscribe_token', '')}" style="color: #6366f1;">Unsubscribe</a>
        </div>
    </body>
    </html>
    """