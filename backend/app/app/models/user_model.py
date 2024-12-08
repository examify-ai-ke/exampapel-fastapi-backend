 
from app.models.base_uuid_model import BaseUUIDModel
from app.models.links_model import LinkGroupUser
from app.models.image_media_model import ImageMedia
from app.schemas.common_schema import  AuthProvider, IGenderEnum
from datetime import datetime
from sqlmodel import BigInteger, Field, SQLModel, Relationship, Column, DateTime, String, Enum
from typing import Optional
# from sqlalchemy_utils import ChoiceType
from pydantic import EmailStr
from uuid import UUID
 
 

# Add Provider Enum


class UserBase(SQLModel):
    # Add model config for arbitrary types
    # model_config = {
    #     "arbitrary_types_allowed": True,
    #     "json_schema_extra": {
    #         "example": {
    #             "first_name": "John",
    #             "last_name": "Doe",
    #             "email": "johndoe@example.com",
    #             "provider": AuthProvider.EMAIL,
    #         }
    #     }
    # }

    first_name: str
    last_name: str
    email: EmailStr = Field(sa_column=Column(String, index=True, unique=True))
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    birthdate: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )  # birthday with timezone
    role_id: UUID | None = Field(default=None, foreign_key="Role.id")
    phone: str | None = None
    gender: IGenderEnum | None = Field(
        default=IGenderEnum.other,
        sa_column=Column(Enum(IGenderEnum), nullable=False, default=IGenderEnum.male))
    email_verified: bool = Field(default=False)
    
    state: str | None = None
    country: str | None = None
    address: str | None = None
    
    # Add new fields for auth provider tracking
    provider: AuthProvider = Field(
        default=AuthProvider.email,
        sa_column=Column(Enum(AuthProvider), nullable=False, default=AuthProvider.email)
    )
    provider_user_id: str | None = Field(
        default=None, 
        sa_column=Column(String, nullable=True)
    )  # Store provider's user ID


class User(BaseUUIDModel, UserBase, table=True):
    hashed_password: str | None = Field(default=None, nullable=False, index=True)
    role: Optional["Role"] = Relationship(  # noqa: F821
        back_populates="users", sa_relationship_kwargs={"lazy": "joined"}
    )
    groups: list["Group"] = Relationship(  # noqa: F821
        back_populates="users",
        link_model=LinkGroupUser,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "User.image_id==ImageMedia.id",
        }
    )
    follower_count: int | None = Field(
        default=None, sa_column=Column(BigInteger(), server_default="0")
    )
    following_count: int | None = Field(
        default=None, sa_column=Column(BigInteger(), server_default="0")
    )
