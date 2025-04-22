from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from pathlib import Path
from jinja2 import Environment, select_autoescape, FileSystemLoader
import logging
from starlette.responses import JSONResponse

# Configure email settings with correct field names
email_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_SMTP_USERNAME,
    MAIL_PASSWORD=settings.MAIL_SMTP_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_SMTP_PORT,
    MAIL_SERVER=settings.MAIL_SMTP_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    MAIL_TLS=True,
    MAIL_SSL=False,
    USE_CREDENTIALS=True,
    # USE_CREDENTIALS=settings.MAIL_USE_CREDENTIALS,
    VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(settings.TEMPLATE_FOLDER),
)
# print(email_config)
# Set up Jinja2 template environment
template_env = Environment(
    loader=FileSystemLoader(settings.TEMPLATE_FOLDER),
    autoescape=select_autoescape(['html', 'xml'])
)

async def send_verification_email(email_to: str, name: str, verification_url: str):
    """
    Send verification email to user
    """
    try:
        # Render email template
        template = template_env.get_template("email_verification.html")
        html_content = template.render(
            name=name,
            verification_url=verification_url,
            company_name=settings.MAIL_FROM_NAME,
            support_email=settings.SUPPORT_EMAIL
        )

        # Create message
        message = MessageSchema(
            subject=f"Verify your email for {settings.PROJECT_NAME}",
            recipients=[email_to],
            body=html_content,
            subtype="html"
        )

        # Send email
        fm = FastMail(email_config)
        await fm.send_message(message)

        logging.info(f"Verification email sent to {email_to}")
        return JSONResponse(status_code=200, content={"message": "Verification email has been sent"})
    except Exception as e:
        logging.error(f"Failed to send verification email to {email_to}: {str(e)}")
        return JSONResponse(status_code=500, content={"message": "Failed to send verification email"})
