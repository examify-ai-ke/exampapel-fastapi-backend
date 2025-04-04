from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
    Enum,
    Column,
    DateTime,
    String,
    Index,
)
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug

# from starlette_admin import TagsField
# from starlette_admin.contrib.sqla import  ModelView
from starlette_admin import fields, TagsField

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

    )
    faculty_id: UUID | None = Field(
        foreign_key="Faculty.id",
        primary_key=True,
        default=None,
  
    )


# Define the base Institution model
class InstitutionBase(SQLModel):
    name: str = Field(unique=True, index=True)
    # description: Optional[str] = Field(nullable=True, default="An Institution of choice")
    description: Optional[str] = Field(
        # nullable=False,
        default="An Institution of choice",
        sa_column=Column(String, index=True),
    )  # Indexed for search
    institution_type: InstitutionTypes = Field(
        sa_column=Column(Enum(InstitutionTypes), nullable=False))
    email: EmailStr = Field(sa_column=Column(String, index=True, unique=True))
    phone_number: Optional[str] = Field(nullable=False)
    # Slug with a validator to generate it from the name
    slug: Optional[str] = Field(default=None, unique=True, index=True)


class Institution(BaseUUIDModel, InstitutionBase, table=True): 

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    logo: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Institution.image_id==ImageMedia.id",
        }
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id", index=True)
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Institution.created_by_id==User.id",
        }
    )

    # Relationships
    campuses: List["Campus"] = Relationship(
        back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"}
    )

    # # Many-to-many relationship with Faculty via a linktable
    faculties: List["Faculty"] = Relationship(
        link_model=InstitutionFacultyLink,
        back_populates="institutions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"}
    )
    # Optional: Explicitly declare table-level indexes (redundant with Field(index=True) but for clarity)
    __table_args__ = (
        Index("idx_institution_name", "name"),  # Already added
        Index("idx_institution_created_at", "created_at"),  # Already added
        Index("idx_institution_email", "email"),  # Already added
        Index("idx_institution_slug", "slug"),  # Already added
        Index("idx_institution_type", "institution_type"),  # Already added
        Index("idx_institution_image_id", "image_id"),  # Already added
        Index("idx_institution_created_by_id", "created_by_id"),  # Already added
    )

    @validator("slug")
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

    @property
    def exams_count(self):
        count=len(self.exam_papers)
        return count
    @property
    def campuses_count(self):
        count_campuses = len(self.campuses)
        return count_campuses

    @property
    def faculties_count(self):
        count_faculties = len(self.faculties)
        return count_faculties
