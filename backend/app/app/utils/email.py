from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr, BaseModel
from app.core.config import settings
from pathlib import Path
from jinja2 import Environment, select_autoescape, FileSystemLoader
import logging
from starlette.responses import JSONResponse
from pydantic import SecretStr
import httpx
# Configure email settings with correct field names
email_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_SMTP_USERNAME,
    MAIL_PASSWORD=SecretStr(settings.MAIL_SMTP_PASSWORD),
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_SMTP_PORT,
    MAIL_SERVER=settings.MAIL_SMTP_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    # VALIDATE_CERTS=settings.MAIL_VALIDATE_CERTS,
    TEMPLATE_FOLDER=Path(settings.TEMPLATE_FOLDER),
)
# print(email_config)
# Set up Jinja2 template environment
template_env = Environment(
    loader=FileSystemLoader(settings.TEMPLATE_FOLDER),
    autoescape=select_autoescape(['html', 'xml'])
)


async def verify_recaptcha(token: str) -> bool:
    """
    Verify Google reCAPTCHA token.

    Args:
        token: The reCAPTCHA token from the frontend

    Returns:
        bool: True if verification successful, False otherwise
    """
    # Bypass reCAPTCHA in development mode for testing
    if settings.is_development:
        logging.info("Development mode: Skipping reCAPTCHA verification")
        return True

    try:
        logging.info(f"Verifying reCAPTCHA token (length: {len(token)})...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.google.com/recaptcha/api/siteverify",
                data={
                    "secret": settings.RECAPTCHA_SECRET_KEY,
                    "response": token
                },
                timeout=10.0
            )
            result = response.json()
            if result.get("success"):
                logging.info("reCAPTCHA verification successful")
                return True
            else:
                error_codes = result.get('error-codes', [])
                logging.warning(f"reCAPTCHA verification failed: {error_codes}")
                # Provide helpful error messages
                if 'invalid-input-response' in error_codes:
                    logging.warning("The response token is invalid or expired. User may need to refresh the page.")
                elif 'invalid-input-secret' in error_codes:
                    logging.warning("The reCAPTCHA secret key is invalid.")
                elif 'bad-request' in error_codes:
                    logging.warning("The request was invalid or malformed.")
                return False
    except Exception as e:
        logging.error(f"reCAPTCHA verification error: {str(e)}")
        return False


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


async def send_contact_email(
    full_name: str,
    email: str,
    institution: str,
    topic: str,
    message: str
):
    """
    Send contact form submission email to support team
    """
    try:
        # Render contact email template
        template = template_env.get_template("contact_email.html")
        html_content = template.render(
            full_name=full_name,
            email=email,
            institution=institution,
            topic=topic,
            message=message,
            company_name=settings.MAIL_FROM_NAME
        )

        # Create message - send to support email
        email_message = MessageSchema(
            subject=f"Contact Form: {topic} - {full_name}",
            recipients=[settings.SUPPORT_EMAIL],
            body=html_content,
            subtype="html",
            reply_to=[email]  # Allow direct reply to the sender (must be a list)
        )

        # Send email
        fm = FastMail(email_config)
        await fm.send_message(email_message)

        logging.info(f"Contact form email sent from {email} - Topic: {topic}")
        return True
    except Exception as e:
        logging.error(f"Failed to send contact email from {email}: {str(e)}")
        return False
