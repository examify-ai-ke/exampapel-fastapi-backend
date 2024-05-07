# from app.models.institution_model import Institution
from app.models.programme_model import ProgrammeDepartmentLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
from app.models.image_media_model import ImageMedia
from app.utils.slugify_string import generate_slug
from pydantic import field_validator, validator


# Department model with ForeignKey to Faculty
class Department(BaseUUIDModel, SQLModel, table=True):
    name: str = Field(nullable=False, unique=True)
    description: Optional[str]
    slug: Optional[str] = Field(default=None, unique=True)

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia | None = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Department.image_id==ImageMedia.id",
        }
    )
    # Foreign key to Faculty
    faculty_id: UUID = Field(foreign_key="Faculty.id", nullable=False)

    # Relationship with Faculty
    faculty: "Faculty" = Relationship(
        back_populates="departments", sa_relationship_kwargs={"lazy": "joined"}
    )

    # Relationship with Faculty
    programmes: List["Programme"] = Relationship(
        link_model=ProgrammeDepartmentLink,
        back_populates="departments",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Department.created_by_id==User.id",
        }
    )

    @validator("slug")
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)
