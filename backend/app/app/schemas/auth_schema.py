from pydantic import BaseModel, EmailStr, Field
from app.schemas.common_schema import AuthProvider
from typing import Optional
from fastapi import  Body

class LoginRequest(BaseModel):
    """
    Schema for login requests, validating login credentials
    """
    email: EmailStr
    password: str 
    provider: AuthProvider = Field(default=AuthProvider.email)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "provider": "email"
            }
        }


class PasswordChange(BaseModel):
    """
    Schema for password change requests
    """
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword456"
            }
        }


class PasswordReset(BaseModel):
    """
    Schema for password reset requests
    """
    email: EmailStr
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """
    Schema for password reset confirmation
    """
    token: str
    new_password: str = Field(..., min_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset-token-from-email",
                "new_password": "newpassword456"
            }
        }


class LogoutResponse(BaseModel):
    """
    Schema for logout response
    """
    success: bool = True
    message: str = "Logged out successfully"
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Logged out successfully"
            }
        } 
