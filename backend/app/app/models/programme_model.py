import enum
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug

# Define ENUM for programme types

class ProgrammeTypes(enum.Enum):
    CERTIFICATE = "Certificate"
    DIPLOMA = "Diploma"
    UNDERGRADUATE = "Undergraduate"
    MASTERS = "Masters"    
    POSTGRADUATE_DIPLOMA = "Postgraduates Diploma"
    PHD_PROGRAMMES = "PhD Programmes"
    ONLINE_MBA = "Online MBA"
    OTHERS = "Others"
    # Set a default value
    DEFAULT = UNDERGRADUATE


# Define the association table for the many-to-many relationship
class ProgrammeDepartmentLink(BaseUUIDModel, SQLModel, table=True):
    programme_id: UUID | None = Field(
        foreign_key="Programme.id",
        primary_key=True,
        default=None,
        unique=True,
    )
    department_id: UUID | None = Field(
        foreign_key="Department.id", primary_key=True, default=None, unique=True
    )


# Define the Programme model
class ProgrammeBase(SQLModel):  
    # Use ENUM for the name field
    name: ProgrammeTypes = Field(
        sa_column=Column(Enum(ProgrammeTypes), nullable=False, unique=True)
    )
    description: Optional[str] = Field(default="Academic Programmes offered by the University/College")


class Programme(BaseUUIDModel, ProgrammeBase, table=True):
    """
    Academic Programmes offered by the Institution  under each Department, e.g Undergraduate programmes, Diploma Programmes, etc
    """
    # Relationship with departments
    departments: List["Department"] = Relationship(
        back_populates="programmes",
        link_model=ProgrammeDepartmentLink,
        sa_relationship_kwargs={"lazy": "joined"},
    )

    # Relationship with courses
    courses: List["Course"] = Relationship(
        back_populates="programme",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    slug: Optional[str] = Field(default=None, unique=True)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Programme.created_by_id==User.id",
        }
    )

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Programme.image_id==ImageMedia.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        convert_to_str = name.value
        return generate_slug(convert_to_str)
