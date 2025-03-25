from app.utils.partial import optional
from app.models.user_model import UserBase
from app.models.group_model import GroupBase
from pydantic import BaseModel
from uuid import UUID
from enum import Enum
from .image_media_schema import IImageMediaRead
from .role_schema import IRoleRead
from pydantic import EmailStr
from datetime import datetime
from app.schemas.common_schema import AuthProvider, IGenderEnum


class IUserCreate(UserBase):
    password: str
    
    class Config:
        # Exclude hashed_password during validation
        hashed_password = None
        from_attributes = True


# All these fields are optional
@optional()
class IUserUpdate(UserBase):
    password: str | None = None
    image_id: UUID | None = None
    
    class Config:
        from_attributes = True


# This schema is used to avoid circular import
class IGroupReadBasic(GroupBase):
    id: UUID


class IUserRead(UserBase):
    id: UUID
    role: IRoleRead | None = None
    groups: list[IGroupReadBasic] | None = []
    image: IImageMediaRead | None = None
    follower_count: int | None = 0
    following_count: int | None = 0
    
    class Config:
        from_attributes = True


class IUserReadWithoutGroups(UserBase):
    id: UUID
    role: IRoleRead | None = None
    image: IImageMediaRead | None = None
    follower_count: int | None = 0
    following_count: int | None = 0
    
    class Config:
        from_attributes = True


class IUserBasicInfo(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    
    class Config:
        from_attributes = True


class IUserStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class ISocialAuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: IUserRead
    
    class Config:
        from_attributes = True


class IEmailVerification(BaseModel):
    email: EmailStr
