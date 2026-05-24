import resend
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key

class EmailService:
    @staticmethod
    def send_security_alert(to_email: str, username: str, title: str, message: str, risk_score: int):
        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY not set. Skipping email.")
            return

        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #2563eb; margin: 0;">RISEN GUARDIAN</h1>
                <p style="color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em;">Security Intelligence Layer</p>
            </div>

            <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h2 style="color: #1e293b; margin-top: 0;">Security Alert for {username}</h2>
                <p style="color: #475569; line-height: 1.6;">
                    {title}
                </p>
                <div style="background-color: {'#fee2e2' if risk_score > 70 else '#fef3c7'}; color: {'#991b1b' if risk_score > 70 else '#92400e'}; padding: 10px; border-radius: 6px; font-weight: bold; text-align: center; margin: 15px 0;">
                    Risk Score: {risk_score}/100
                </div>
                <p style="color: #475569;">
                    {message}
                </p>
            </div>

            <div style="text-align: center;">
                <a href="https://risenonchain.net/guardian" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                    View Detailed Report
                </a>
            </div>

            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 20px 0;" />

            <p style="color: #94a3b8; font-size: 12px; text-align: center;">
                This is an automated security alert from RISEN Guardian. If you did not perform this scan, please secure your account.
            </p>
        </div>
        """

        try:
            params = {
                "from": settings.from_email,
                "to": [to_email],
                "subject": f"🛡️ RISEN Guardian: {title}",
                "html": html_content,
            }

            resend.Emails.send(params)
            logger.info(f"Security alert email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {e}")
