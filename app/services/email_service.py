import requests
from flask import current_app, url_for
from itsdangerous import URLSafeTimedSerializer

class EmailService:

    @classmethod
    def send_claim_profile_email(cls, to_email, researcher_uuid, user_id):
        token = cls.generate_token({'r_uuid': researcher_uuid, 'u_id': user_id}, 'claim-salt')
        verify_url = url_for('auth.verify_claim', token=token, _external=True)
        content = f"""
        <h2 style='color:#002147;margin-top:0;'>Action Required: Profile Claim Request</h2>
        <p>Hello,</p>
        <p>A user on <strong>ResearchGraph</strong> has just requested to claim the research profile associated with this email address.</p>
        <p>If this was you, please click the secure button below to verify your identity and instantly take control of your interactive collaboration network:</p>
        <p style='text-align:center;'>
            <a href='{verify_url}' style='display:inline-block;padding:12px 24px;background-color:#002147;color:#ffffff;text-decoration:none;border-radius:6px;font-weight:bold;margin:20px 0;'>Verify & Claim Profile</a>
        </p>
        <p style='color:#dc3545;font-weight:bold;'>If you did NOT request this, please completely ignore this email.</p>
        <p>No action will be taken on your profile, and the unauthorized claim request will automatically expire.</p>
        <hr style='border:none;border-top:1px solid #eee;margin:20px 0;'/>
        <p style='color:#777;font-size:0.85em;'>This verification link securely expires in 1 hour.</p>
        """
        html = cls.get_html_template(content)
        text = f"Verify your profile claim here: {verify_url}"
        return cls.send_email(to_email, "ResearchGraph - Verify Profile Claim", html, text)

    @staticmethod
    def get_serializer():
        return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

    @staticmethod
    def generate_token(email, salt):
        serializer = EmailService.get_serializer()
        return serializer.dumps(email, salt=salt)

    @staticmethod
    def verify_token(token, salt, expiration=3600):
        serializer = EmailService.get_serializer()
        try:
            email = serializer.loads(token, salt=salt, max_age=expiration)
            return email
        except Exception:
            return None


    @staticmethod
    def get_html_template(content_html):
        return f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333333; line-height: 1.6;">
            <div style="background-color: #002147; padding: 25px; text-align: center; border-radius: 6px 6px 0 0;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 1px;">ResearchGraph</h1>
            </div>
            <div style="padding: 40px 30px; background-color: #ffffff; border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0;">
                {content_html}
            </div>
            <div style="background-color: #f8f9fa; padding: 30px; border-radius: 0 0 6px 6px; border: 1px solid #e0e0e0; border-top: none;">
                <p style="margin: 0 0 15px 0; font-size: 15px; color: #555555;">Best regards,</p>
                <table cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td>
                            <p style="margin: 0 0 4px 0; font-weight: bold; font-size: 16px; color: #002147;">Indrajit Ghosh</p>
                            <p style="margin: 0 0 4px 0; font-size: 14px; color: #666666;">Founder and Developer of ResearchGraph</p>
                            <p style="margin: 0 0 8px 0; font-size: 14px; color: #666666;">Postdoc Researcher in Mathematics</p>
                            <p style="margin: 0; font-size: 14px;">
                                <a href="https://indrajitghosh.onrender.com" style="color: #0d6efd; text-decoration: none; font-weight: 500;">https://indrajitghosh.onrender.com</a>
                            </p>
                        </td>
                    </tr>
                </table>
            </div>
        </div>
        """

    @staticmethod
    def send_email(to_email, subject, body_html, body_text):
        api_url = current_app.config.get('HERMES_API_URL')
        api_key = current_app.config.get('HERMES_API_KEY')
        bot_id = current_app.config.get('HERMES_EMAILBOT_ID')
        
        if not api_url or not api_key:
            current_app.logger.warning("Hermes API not configured. Mocking email.")
            print(f"\n--- [Mock Email] To: {to_email} | Subject: {subject} ---")
            print(f"[HTML Content Sent Only]")
            return {"success": True, "mocked": True}
            
        endpoint = f"{api_url.rstrip('/')}/api/v1/send-email"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "to": [to_email],
            "subject": subject,
            "from_name": "ResearchGraph Admin",
            "email_html_text": body_html
        }
        if bot_id:
            payload["bot_id"] = bot_id
            
        try:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=12)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            current_app.logger.error(f"Email dispatch failed: {e}")
            return {"success": False, "error": str(e)}

    @classmethod
    def send_verification_email(cls, to_email):
        token = cls.generate_token(to_email, 'email-verify-salt')
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        content = f"<h2 style='color:#002147;margin-top:0;'>Welcome to ResearchGraph!</h2><p>Please verify your email by clicking the link below:</p><p><a href='{verify_url}' style='display:inline-block;padding:12px 25px;background-color:#0d6efd;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;margin:20px 0;'>Verify Email Address</a></p><p style='color:#777;font-size:0.9em;'>This link securely expires in 1 hour.</p>"
        html = cls.get_html_template(content)
        text = f"Welcome to ResearchGraph! Verify your email here: {verify_url} (Expires in 1 hour)"
        return cls.send_email(to_email, "Verify Your ResearchGraph Account", html, text)

    @classmethod
    def send_password_reset_email(cls, to_email):
        token = cls.generate_token(to_email, 'password-reset-salt')
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        content = f"<h2 style='color:#002147;margin-top:0;'>Password Reset Request</h2><p>Click the link below to reset your password:</p><p><a href='{reset_url}' style='display:inline-block;padding:12px 25px;background-color:#dc3545;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;margin:20px 0;'>Reset Password</a></p><p>This link expires in 1 hour. If you didn't request this, ignore this email.</p>"
        html = cls.get_html_template(content)
        text = f"Reset your password here: {reset_url} (Expires in 1 hour)"
        return cls.send_email(to_email, "ResearchGraph Password Reset", html, text)
