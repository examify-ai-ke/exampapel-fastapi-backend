import enum
from sqlmodel import (
    Field,
    Relationship,
    SQLModel,
    Enum,
    Column,
    DateTime,
    String,
    UniqueConstraint
)
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug


# Define the association table for the many-to-many relationship
class CourseModuleLink(BaseUUIDModel, SQLModel, table=True):
    course_id: UUID | None = Field(
        foreign_key="Course.id",
        primary_key=True,
        default=None,
    )
    module_id: UUID | None = Field(
        foreign_key="Module.id", primary_key=True, default=None
    )
    UniqueConstraint("course_id", "module_id", name="idx_course_id_module_id"),


class Module(BaseUUIDModel, SQLModel, table=True):
    """_summary_
    A unit is an academic module which forms part of a course, which represents a credit point value that contributes towards a course
    """
    name: str = Field(nullable=False, unique=True)
    slug: Optional[str] = Field(default=None, unique=True)
    unit_code: str = Field(default=None, unique=True)
    description: Optional[str] = Field(
        default="An academic module/unit that forms part of the course"
    )

    # Relationship with courses
    courses: List["Course"] = Relationship(
        back_populates="modules",
        link_model=CourseModuleLink,
        sa_relationship_kwargs={"lazy": "joined"}
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Module.created_by_id==User.id",
        }
    )

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Module.image_id==ImageMedia.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)
