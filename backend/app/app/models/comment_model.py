from sqlmodel import Field, Relationship, SQLModel, Column
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
from sqlalchemy.dialects.postgresql import JSONB
from typing import Dict, List, Optional, Any


class CommentBase(SQLModel):
    text: Optional[Dict[str, Any]] = Field(
        default_factory={}, sa_column=Column(JSONB, nullable=True)
    )


class Comment(BaseUUIDModel, CommentBase, table=True):
    likes: int = Field(default=0)
    dislikes: int = Field(default=0)

    # Relationship to Answer
    answer_id: UUID = Field(foreign_key="Answer.id")
    answer: "Answer" = Relationship(back_populates="comments")

    # User who created the comment
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Comment.created_by_id==User.id",
        }
    )

    # Self-referencing for replies
    parent_id: UUID | None = Field(
        default=None, foreign_key="Comment.id", nullable=True
    )
    parent: Optional["Comment"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={"remote_side": "Comment.id", "lazy": "selectin"},
    )
    replies: List["Comment"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
