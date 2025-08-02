from pydantic import BaseModel, EmailStr, Field, validator
from app.schemas.common_schema import AuthProvider
from typing import Optional
from fastapi import  Body
import re

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
    Schema for password change requests with enhanced security requirements
    """
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """
        Validate password strength requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter  
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        
        # Check for common weak patterns
        weak_patterns = [
            r'(.)\1{2,}',  # Three or more consecutive identical characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError('Password contains weak patterns. Please choose a stronger password.')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "OldPass123!",
                "new_password": "NewSecure456@"
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
    Schema for password reset confirmation with enhanced security
    """
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        """
        Apply the same password strength validation as PasswordChange
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>)')
        
        # Check for common weak patterns
        weak_patterns = [
            r'(.)\1{2,}',  # Three or more consecutive identical characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, v.lower()):
                raise ValueError('Password contains weak patterns. Please choose a stronger password.')
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset-token-from-email",
                "new_password": "NewSecure456@"
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
