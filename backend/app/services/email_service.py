"""
Email Service — Resend integration for transactional emails.

Currently used for:
- Admin password reset emails
"""

import logging
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


def _init_resend():
    """Initialize Resend with API key."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY not set — emails will not be sent")
        return False
    resend.api_key = settings.resend_api_key
    return True


async def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Send a password reset email to the admin.

    Args:
        to_email: Recipient email address
        reset_url: Full URL with reset token

    Returns:
        True if sent successfully
    """
    if not _init_resend():
        return False

    try:
        resend.Emails.send({
            "from": "LENA Admin <onboarding@resend.dev>",
            "to": [to_email],
            "subject": "LENA Admin — Password Reset",
            "html": f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 24px;">
                <div style="text-align: center; margin-bottom: 32px;">
                    <div style="display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; border-radius: 50%; background: linear-gradient(135deg, #1B6B93, #145372);">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
                            <path d="M12 2C12 2 14.5 8.5 15.5 9.5C16.5 10.5 22 12 22 12C22 12 16.5 13.5 15.5 14.5C14.5 15.5 12 22 12 22C12 22 9.5 15.5 8.5 14.5C7.5 13.5 2 12 2 12C2 12 7.5 10.5 8.5 9.5C9.5 8.5 12 2 12 2Z"/>
                        </svg>
                    </div>
                </div>
                <h1 style="font-size: 20px; font-weight: 700; color: #1a1a2e; text-align: center; margin-bottom: 8px;">
                    Password Reset
                </h1>
                <p style="font-size: 14px; color: #64748b; text-align: center; margin-bottom: 32px; line-height: 1.6;">
                    A password reset was requested for the LENA Admin Console.
                    Click the button below to set a new password.
                </p>
                <div style="text-align: center; margin-bottom: 32px;">
                    <a href="{reset_url}"
                       style="display: inline-block; padding: 12px 32px; background: linear-gradient(135deg, #1B6B93, #145372); color: white; text-decoration: none; border-radius: 8px; font-size: 14px; font-weight: 600;">
                        Reset Password
                    </a>
                </div>
                <p style="font-size: 12px; color: #94a3b8; text-align: center; line-height: 1.6;">
                    This link expires in 15 minutes. If you did not request this, ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
                <p style="font-size: 11px; color: #cbd5e1; text-align: center;">
                    LENA — Literature and Evidence Navigation Agent
                </p>
            </div>
            """,
        })
        logger.info(f"Password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False
