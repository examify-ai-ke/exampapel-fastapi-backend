from app.models.institution_model import Institution, InstitutionFacultyLink
from app.models.department_model import Department
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from app.utils.slugify_string import generate_slug
from pydantic import  field_validator, validator
from slugify import slugify

# Updated Faculty model to reflect the connection to InstitutionFaculty
class Faculty(BaseUUIDModel, SQLModel, table=True):
    """
    Faculty or School of an institution. e.g Faculty of Enginering , Technology  School/Faculty.
    """
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = None
    slug: Optional[str] = Field(default=None, unique=True)

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia | None = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Faculty.image_id==ImageMedia.id",
        }
    )

    # Relationships
    # Many-to_many Relationship with Institution
    institutions: List[Institution] = Relationship(
        back_populates="faculties",
        link_model=InstitutionFacultyLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    departments: List[Department] = Relationship(
        back_populates="faculty", sa_relationship_kwargs={"lazy": "selectin"}
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",    
            "primaryjoin": "Faculty.created_by_id==User.id",
        }
    )

    @property
    def total_institutions(self):
        total=len(self.institutions)
        return total

    @property
    def total_departments(self):
        total=len(self.departments)
        return total

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

    institution_count = total_institutions
    department_count = total_departments
