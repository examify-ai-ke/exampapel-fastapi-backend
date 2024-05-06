# from app.models.institution_model import Institution
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
from app.models.image_media_model import ImageMedia
from app.utils.slugify_string import generate_slug
from pydantic import field_validator, validator

# Department model with ForeignKey to Faculty
class Department(SQLModel, BaseUUIDModel, table=True):
    name: str = Field(nullable=False, unique=True)
    description: Optional[str]
    slug: Optional[str] = Field(default=None, unique=True)

    # Foreign key to Faculty
    faculty_id: int = Field(foreign_key="faculty.id", nullable=False)

    # Relationship with Faculty
    faculty: "Faculty" = Relationship(back_populates="departments")

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Department.created_by_id==User.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        if value:
            return value
        name = values.get("name", "")
        return generate_slug(name)
