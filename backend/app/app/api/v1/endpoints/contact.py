import logging
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter
from app.schemas.response_schema import IPostResponseBase, create_response
from app.schemas.contact_schema import ContactCreate, ContactResponse
from app.schemas.common_schema import IMetaGeneral
from app.api import deps
from app.utils.email import send_contact_email

router = APIRouter()


@router.post("", dependencies=[Depends(RateLimiter(times=20, minutes=60))], response_model=IPostResponseBase[ContactResponse])
async def send_contact_message(
    contact_data: ContactCreate,
    meta_data: IMetaGeneral = Depends(deps.get_general_meta),
) -> IPostResponseBase[ContactResponse]:
    """
    Send a contact form message to the support team.

    Rate limited to 5 submissions per hour per IP to prevent spam.
    The message will be sent to the support email configured in settings.
    """
    print(contact_data)
    # Verify reCAPTCHA token
    from app.utils.email import verify_recaptcha

    recaptcha_valid = await verify_recaptcha(contact_data.recaptcha_token)
    if not recaptcha_valid:
        response_data = ContactResponse(
            success=False,
            message="reCAPTCHA verification failed. Please try again."
        )
        return create_response(
            meta=meta_data,
            data=response_data,
            message="reCAPTCHA verification failed"
        )

    logging.info(f"Contact form submission from {contact_data.email} - Topic: {contact_data.topic}")

    # Send email using the email utility
    email_sent = await send_contact_email(
        full_name=contact_data.full_name,
        email=contact_data.email,
        institution=contact_data.institution,
        topic=contact_data.topic.value,
        message=contact_data.message
    )

    if not email_sent:
        logging.error(f"Failed to send contact email from {contact_data.email}")
        response_data = ContactResponse(
            success=False,
            message="Failed to send your message. Please try again later."
        )
        return create_response(
            meta=meta_data,
            data=response_data,
            message="Failed to send contact message"
        )

    logging.info(f"Contact form email successfully sent from {contact_data.email}")
    response_data = ContactResponse(
        success=True,
        message="Your message has been sent successfully. We will get back to you soon."
    )
    return create_response(
        meta=meta_data,
        data=response_data,
        message="Contact message sent successfully"
    )
