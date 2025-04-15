from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.utils.partial import optional


class BlockData(BaseModel):
    text: str


class Block(BaseModel):
    id: str
    data: Dict[str, Any]
    type: str


class CommentTextSchema(BaseModel):
    time: int
    blocks: list[Block]

    class Config:
        json_schema_extra = {
            "example": {
                "time": 1742156891260,
                "blocks": [
                    {
                        "id": "dCcbQeoht12",
                        "data": {
                            "text": "Write a Python function that calculates the factorial of a given number. Explain your code."
                        },
                        "type": "paragraph",
                    }
                ],
            }
        }


class CommentBase(BaseModel):
    text: CommentTextSchema
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
    text: CommentTextSchema
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
