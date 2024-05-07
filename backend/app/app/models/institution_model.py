from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug

# Define an enumeration for institution types
class InstitutionTypes(enum.Enum):
    UNIVERSITY = "University"
    COLLEGE = "College"
    TVET = "TVET"
    OTHER = "Other"


# Define the link model for the many-to-many relationship between Institution and  Faculty
class InstitutionFacultyLink(BaseUUIDModel, SQLModel, table=True):
    institution_id: UUID | None = Field(
        foreign_key="Institution.id",
        primary_key=True,
        default=None,
        unique=True,
    )
    faculty_id: UUID | None = Field(
        foreign_key="Faculty.id",
        primary_key=True,
        default=None,
        unique=True
    )



# Define the base Institution model
class InstitutionBase(SQLModel):
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = None
    institution_type: InstitutionTypes = Field(
        sa_column=Column(Enum(InstitutionTypes), nullable=False))
    email: EmailStr = Field(sa_column=Column(String, index=True, unique=True))
    phone_number: Optional[str] = Field(nullable=False)
    
    # Slug with a validator to generate it from the name
    slug: Optional[str] = Field(default=None, unique=True)
    
    @validator("slug")
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

class Institution(BaseUUIDModel, InstitutionBase, table=True): 

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    logo: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Institution.image_id==ImageMedia.id",
        }
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Institution.created_by_id==User.id",
        }
    )
    # Relationships
    campuses: List["Campus"] = Relationship(
        back_populates="institution", sa_relationship_kwargs={"lazy": "joined"}
    )

    # # Many-to-many relationship with Faculty via a linktable
    faculties: List["Faculty"] = Relationship(
        link_model=InstitutionFacultyLink,
        back_populates="institutions",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    # # Pydantic validator to generate a slug if not provided
    # @field_validator("slug")
    # def set_slug(cls, value, values):
    #     if value is None:
    #         name = values.get("name", "")
    #         return generate_slug(name)  # Create a slug from the name
    #     return value
