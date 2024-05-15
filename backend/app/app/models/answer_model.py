from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String,Table
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia
from sqlalchemy.dialects.postgresql import TEXT
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug

# class AnswerAssociationLink(BaseUUIDModel, SQLModel, table=True):
#     parent_id:UUID | None = Field(foreign_key="Answer.id",primary_key=True,
#         default=None)
#     child_id: UUID | None = Field(
#         foreign_key="Answer.id", primary_key=True, default=None
#     )


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
    parent_id: UUID | None = Field(default=None, foreign_key="Answer.id", nullable=True)
    parent: Optional["Answer"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Answer.id", "lazy": "joined"},
    )
    children: List["Answer"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "lazy": "joined",
            "remote_side": "Answer.parent_id","join_depth":2
        },
    )

    # parents: List["Answer"] = Relationship(
    #     link_model=AnswerAssociationLink,
    #     sa_relationship_kwargs={
    #         "primaryjoin": "Answer.id == AnswerAssociationLink.child_id",
    #         "secondaryjoin": "Answer.id == AnswerAssociationLink.parent_id",
    #         "lazy": "joined",
    #     },
    # )
    # children: List["Answer"] = Relationship(
    #     link_model=AnswerAssociationLink,
    #     sa_relationship_kwargs={
    #         "primaryjoin": "Answer.id == AnswerAssociationLink.parent_id",
    #         "secondaryjoin": "Answer.id == AnswerAssociationLink.child_id",
    #         "lazy": "joined",
    #     },
    # )

    main_question_id: UUID | None = Field(default=None, foreign_key="MainQuestion.id")
    main_question: Optional["MainQuestion"] = Relationship(
        back_populates="answers"
    )

    sub_question_id: UUID | None = Field(default=None, foreign_key="SubQuestion.id")
    sub_question: Optional["SubQuestion"] = Relationship(
        back_populates="answers"
    )



