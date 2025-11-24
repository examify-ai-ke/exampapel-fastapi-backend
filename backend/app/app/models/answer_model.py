from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String,Table
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB
from typing import Any, Dict, List, Optional
from app.models.image_media_model import ImageMedia
from sqlalchemy.dialects.postgresql import TEXT
from pydantic import EmailStr, validator
from app.utils.slugify_string import generate_slug
from sqlalchemy import UniqueConstraint
 
from app.models.comment_model import Comment  # Add this import

# Like/Dislike tracking table
class AnswerVote(BaseUUIDModel, table=True):
    """Track user votes (likes/dislikes) on answers"""
    answer_id: UUID = Field(foreign_key="Answer.id", nullable=False)
    user_id: UUID = Field(foreign_key="User.id", nullable=False)
    vote_type: str = Field(nullable=False)  # "like" or "dislike"
    
    __table_args__ = (
        UniqueConstraint("answer_id", "user_id", name="_answer_user_vote_uc"),
    )

class AnswerBase(SQLModel):  
    text: Optional[Dict[str, Any]] = Field(
        default_factory={}, sa_column=Column(JSONB, nullable=True)
    )


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
        sa_relationship_kwargs={"remote_side": "Answer.id", "lazy": "selectin"},
    )
    # child_id: UUID | None = Field(default=None, foreign_key="Answer.id", nullable=True)
    # children: List["Answer"] = Relationship(
    #     back_populates="parent",
    #     sa_relationship_kwargs={
    #         "lazy": "joined",
    #         "remote_side": "Answer.parent_id","join_depth":2
    #     },
    # )
    children: List["Answer"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "lazy": "selectin",  # More efficient for collections than "joined"
            "remote_side": "Answer.parent_id",
        },
    )

    question_id: UUID | None = Field(default=None, foreign_key="Question.id")
    question: Optional["Question"] = Relationship(
        back_populates="answers",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    comments: List["Comment"] = Relationship(
        back_populates="answer",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
