from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from sqlalchemy.dialects.postgresql import TEXT
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug


# Define the Course model
class AnswerBase(SQLModel):  
    text: str = Field(sa_column=Column(TEXT, nullable=False, unique=False))


class Answer(BaseUUIDModel,AnswerBase, table=True):
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)
    reviewed: bool = Field(default=False)
    auto_answer: bool = Field(default=False)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Answer.created_by_id==User.id",
        }
    )
    parent_id: UUID | None = Field(default=None, foreign_key="Answer.id")
    parent: Optional["Answer"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Answer.id"},
    )
    children: Optional[List["Answer"]] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"lazy": "selectin"},
        # dict(remote_side="Answer.parent_id"),
    )

    main_question_id: UUID | None = Field(default=None, foreign_key="MainQuestion.id")
    main_question: Optional["MainQuestion"] = Relationship(
        back_populates="answers"
    )

    sub_question_id: UUID | None = Field(default=None, foreign_key="SubQuestion.id")
    sub_question: Optional["SubQuestion"] = Relationship(
        back_populates="answers"
    )


# class Course(BaseUUIDModel, CourseBase, table=True):
#     """_summary_
#         A Specific Course offered by an individual institution under a programme. e.g BSCIT
#     """
#     slug: Optional[str] = Field(default=None, unique=True)

#     # Foreign key to Programme
#     programme_id: UUID = Field(foreign_key="Programme.id", nullable=False)

#     # Relationship with Programme
#     programme: "Programme" = Relationship(
#         back_populates="courses"
#     )

#     exam_papers: List["ExamPaper"] = Relationship(
#         back_populates="course",
#         sa_relationship_kwargs={"lazy": "joined"},
#     )

#     created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
#     created_by: "User" = Relationship(  # noqa: F821
#         sa_relationship_kwargs={
#             "lazy": "joined",
#             "primaryjoin": "Course.created_by_id==User.id",
#         }
#     )

#     image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
#     image: ImageMedia = Relationship(
#         sa_relationship_kwargs={
#             "lazy": "joined",
#             "primaryjoin": "Course.image_id==ImageMedia.id",
#         }
#     )

#     # Relationship with CourseModule/Unit
#     modules: List["Module"] = Relationship(
#         link_model=CourseModuleLink,
#         back_populates="courses",
#         sa_relationship_kwargs={"lazy": "joined"},
#     )

#     @validator("slug", pre=True, always=True)
#     def set_slug(cls, value, values):
#         name = values.get("name", "")
#         return generate_slug(name)
