from app.models.exam_paper_model import ExamPaper
# from app.models.faculty_model import Faculty
from app.models.user_model import User
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
from sqlalchemy import Text
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional, TYPE_CHECKING
from app.models.image_media_model import ImageMedia
from sqlalchemy.dialects.postgresql import JSONB
from pydantic import EmailStr, validator
from app.utils.slugify_string import generate_slug
from fastapi_cache.decorator import cache

if TYPE_CHECKING:
    from app.models.campus_model import Campus

# from starlette_admin import TagsField
# from starlette_admin.contrib.sqla import  ModelView
# from starlette_admin import fields, TagsField

# Define an enumeration for institution types
class InstitutionCategory(enum.Enum):
    UNIVERSITY = "University"
    COLLEGE = "College"
    TVET = "TVET"
    OTHER = "Other"

# Define an enumeration for institution ownership types
class InstitutionType(enum.Enum):
    PUBLIC = "Public"
    PRIVATE = "Private"
    OTHER = "Other"

# Address model for institutions and campuses
class Address(BaseUUIDModel, SQLModel, table=True):
    address_line1: str = Field(nullable=False)  # Required field
    address_line2: Optional[str] = Field(default=None, nullable=True)
    county: Optional[str] = Field(default=None, nullable=True)
    constituency: Optional[str] = Field(default=None, nullable=True)
    zip_code: Optional[str] = Field(default=None, nullable=True)
    telephone: Optional[str] = Field(default=None, nullable=True)
    telephone2: Optional[str] = Field(default=None, nullable=True)
    email: Optional[EmailStr] = Field(default=None, nullable=True)
    website: Optional[str] = Field(default=None, nullable=True)
    country: str = Field(nullable=False)  # Required field

    # Relationships
    institution_id: Optional[UUID] = Field(default=None, foreign_key="Institution.id", nullable=True)
    institution: Optional["Institution"] = Relationship(back_populates="address")

    campus_id: Optional[UUID] = Field(default=None, foreign_key="Campus.id", nullable=True)
    campus: Optional["Campus"] = Relationship(back_populates="address")

    __table_args__ = (
        Index("idx_address_institution_id", "institution_id"),
        Index("idx_address_campus_id", "campus_id"),
    )


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
    name: str = Field(unique=True)
    description: Optional[str] = Field(
        default="An Institution of choice",
        sa_column=Column(String, nullable=True),
    )  # Indexed for search
    category: InstitutionCategory = Field(default=InstitutionCategory.UNIVERSITY,
        sa_column=Column(Enum(InstitutionCategory), nullable=True)
    )
    # email: EmailStr = Field(sa_column=Column(String, unique=True))
    # phone_number: Optional[str] = Field(nullable=True)

    # New optional fields
    key: Optional[str] = Field(default=None, nullable=True)
    location: Optional[str] = Field(default=None, nullable=True) #county location of the instituion
    kuccps_institution_url: Optional[str] = Field(default=None, nullable=True)
    institution_type: Optional[InstitutionType] = Field(
        default=InstitutionType.PUBLIC, 
        sa_column=Column(Enum(InstitutionType), nullable=True)
    )
    full_profile: Optional[str] = Field(
        default=None,sa_column=Column(Text)
    )
    parent_ministry: Optional[str] = Field(default=None, nullable=True)
    # Slug with a validator to generate it from the name
    tags: Optional[List[str]] = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="List of tags for categorization",
    )


class Institution(BaseUUIDModel, InstitutionBase, table=True): 
    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    logo: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",  # Changed from "joined" to "selectin" for better performance
        }
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id", index=True)
    created_by: User = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",  # Changed from "selectin" to optimize loading
        }
    )

    # Relationships
    campuses: List["Campus"] = Relationship(
        back_populates="institution",
        sa_relationship_kwargs={
            "lazy": "selectin",  # Changed from "selectin" to optimize loading
        },
    )

    # Address relationship
    address: Optional[Address] = Relationship(
        back_populates="institution",
        sa_relationship_kwargs={
            "lazy": "joined",  # Changed from "selectin" to optimize loading
        },
    )

    # Many-to-many relationship with Faculty via a linktable
    faculties: List["Faculty"] = Relationship(
        link_model=InstitutionFacultyLink,
        back_populates="institutions",
        sa_relationship_kwargs={
            "lazy": "selectin",  # Changed from "selectin" to optimize loading
        },
    )
    slug: Optional[str] = Field(default=None, unique=True)
    exam_papers: List[ExamPaper] = Relationship(
        back_populates="institution",
        sa_relationship_kwargs={
            "lazy": "selectin",  # Changed from "selectin" to optimize loading
        },
    )
    # Optional: Explicitly declare table-level indexes (redundant with Field(index=True) but for clarity)
    __table_args__ = (
        Index("idx_institution_name", "name"),  # Already added
        Index("idx_institution_created_at", "created_at"),  # Already added
        Index("idx_institution_slug", "slug"),  # Already added
        Index("idx_institution_category", "category"),  # Changed from institution_type
        Index("idx_institution_type", "institution_type"),  # Added index for new institution_type
        Index("idx_institution_image_id", "image_id"),  # Already added
        Index("idx_institution_created_by_id", "created_by_id"),  # Already added
        Index("idx_institution_tags", "tags", postgresql_using="gin"),
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, v, values):
        if v:
            return v
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
