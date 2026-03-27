from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class ContactTopic(str, Enum):
    """Contact form topic options"""
    strategic_partnership = "Strategic Partnership"
    general_inquiry = "General Inquiry"
    technical_support = "Technical Support"
    sales = "Sales"
    feedback = "Feedback"
    other = "Other"


class ContactCreate(BaseModel):
    """Schema for creating a contact form submission"""
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the contact")
    email: EmailStr = Field(..., description="Work email address")
    institution: str = Field(..., min_length=2, max_length=200, description="Institution or Organization name")
    topic: ContactTopic = Field(default=ContactTopic.general_inquiry, description="Topic of the contact")
    message: str = Field(..., min_length=10, max_length=2000, description="Contact message")
    recaptcha_token: str = Field(..., description="Google reCAPTCHA token for verification")

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Dr. John Doe",
                "email": "john.doe@university.edu",
                "institution": "University of Nairobi",
                "topic": "Strategic Partnership",
                "message": "We are interested in exploring partnership opportunities..."
            }
        }


class ContactResponse(BaseModel):
    """Schema for contact form submission response"""
    success: bool
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Your message has been sent successfully. We will get back to you soon."
            }
        }
