import enum
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, validator
from app.utils.slugify_string import generate_slug

# Define ENUM for programme types

class ProgrammeTypes(enum.Enum):
    CERTIFICATE = "Certificate"
    DIPLOMA = "Diploma"
    BACHELORS = "Bachelors/Undergraduate"
    MASTERS = "Masters"
    DOCTORATE = "Doctorate"
    POSTGRADUATE_DIPLOMA = "Postgraduate Diploma"
    PHD_PROGRAMMES = "PhD Programmes"
    ONLINE_MBA = "Online MBA"
    OTHERS = "Others"


# Define the association table for the many-to-many relationship
class ProgrammeDepartmentLink(BaseUUIDModel, SQLModel, table=True):
    programme_id: UUID | None = Field(
        foreign_key="Programme.id",
        primary_key=True,
        default=None,
    )
    department_id: UUID | None = Field(
        foreign_key="Department.id", primary_key=True, default=None
    )


# Define the Programme model
class ProgrammeBase(SQLModel):  
    # Use ENUM for the name field
    name: ProgrammeTypes = Field(
        default=ProgrammeTypes.BACHELORS,
        sa_column=Column(Enum(ProgrammeTypes), nullable=False, unique=True),
    )
    description: Optional[str] = Field(
        default="A specific type of university/College program (e.g., Bachelors, Masters. etc)"
    )


class Programme(BaseUUIDModel, ProgrammeBase, table=True):
    """
    Academic Programmes offered by the Institution  under each Department, e.g Undergraduate programmes, Diploma Programmes, etc
    """
    # Relationship with departments
    departments: List["Department"] = Relationship(
        back_populates="programmes",
        link_model=ProgrammeDepartmentLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    # Relationship with courses
    courses: List["Course"] = Relationship(
        back_populates="programme",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    slug: Optional[str] = Field(default=None, unique=True)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Programme.created_by_id==User.id",
        }
    )

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Programme.image_id==ImageMedia.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        convert_to_str = name.value
        return generate_slug(convert_to_str)

    @property
    def departments_count(self):
        return len(self.departments)

    @property
    def courses_count(self):
        return len(self.courses)

    @property
    def exam_papers_count(self):
        return sum(len(course.exam_papers) for course in self.courses)
