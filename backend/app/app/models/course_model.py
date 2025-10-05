from app.models.module_model import CourseModuleLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia

from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug


# Define the Course model
class CourseBase(SQLModel):  
    # Use ENUM for the name field
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = Field(default="Specific Institution Course/Programme offered by the Institution e.g BSc IT")


class Course(BaseUUIDModel, CourseBase, table=True):
    """_summary_
        A Specific Course offered by an individual institution under a programme. e.g BSCIT
    """
    slug: Optional[str] = Field(default=None, unique=True)
    course_acronym: Optional[str] = Field(default=None, unique=True)
    # Foreign key to Programme
    programme_id: UUID = Field(foreign_key="Programme.id", nullable=False)

    # Relationship with Programme
    programme: "Programme" = Relationship(
        back_populates="courses",
        sa_relationship_kwargs={"lazy": "selectin"}     
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="course",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Course.created_by_id==User.id",
        }
    )

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    image: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Course.image_id==ImageMedia.id",
        }
    )

    # Relationship with CourseModule/Unit
    modules: List["Module"] = Relationship(
        link_model=CourseModuleLink,
        back_populates="courses",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

    @property
    def modules_count(self):
        return len(self.modules)

    @property
    def exam_papers_count(self):
        return len(self.exam_papers)
