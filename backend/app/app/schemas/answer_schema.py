from typing import Any, Dict, List, Optional
from app.utils.partial import optional
from uuid import UUID
from pydantic import   BaseModel


class AnswerBase(BaseModel):
    # text: str
    text: Optional[Dict[str, Any]]
    parent_id: Optional[UUID] = None
    main_question_id: Optional[UUID] = None
    sub_question_id: Optional[UUID] = None


@optional()
class AnswerUpdate(AnswerBase):
    id: UUID
    pass


class AnswerCreate(AnswerBase):
    pass

class ChildrenReadForAnswerRead(BaseModel):
    id: Optional[UUID]
    text: Optional[Dict[str, Any]]
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    
    class Config:
        from_attributes = True


class ParentReadForAnswerRead(BaseModel):
    id: UUID
    text: Optional[Dict[str, Any]]


class AnswerRead(AnswerBase):
    id: UUID
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    auto_answer: bool = False
    parent: Optional[ParentReadForAnswerRead] = None
    children: Optional[List[ChildrenReadForAnswerRead]] = None

    class Config:
        from_attributes = True

AnswerRead.model_rebuild(force=True)
# Handle forward references for self-referential models
