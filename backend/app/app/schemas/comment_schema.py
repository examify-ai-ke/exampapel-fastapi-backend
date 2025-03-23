from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.utils.partial import optional

class CommentBase(BaseModel):
    text: Optional[Dict[str, Any]]
    answer_id: UUID
    parent_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class CommentCreate(CommentBase):
    pass


@optional()
class CommentUpdate(CommentBase):
    id: UUID


class CommentReplyRead(BaseModel):
    id: UUID
    text: Optional[Dict[str, Any]]
    likes: int = 0
    dislikes: int = 0
    created_by_id: Optional[UUID] = None
    created_at: datetime
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class CommentRead(CommentBase):
    id: UUID
    likes: int = 0
    dislikes: int = 0
    created_by_id: Optional[UUID] = None
    created_at: datetime
    
    # Make replies Optional[List] with default=None instead of relying on the relationship
    # replies: Optional[List[CommentReplyRead]] = []
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class CommentCountSchema(BaseModel):
    count: int
    
    class Config:
        from_attributes = True


# Handle forward references
CommentRead.model_rebuild(force=True)
