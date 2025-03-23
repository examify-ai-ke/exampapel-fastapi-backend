from typing import Any, Dict, List, Optional
from app.utils.partial import optional
from uuid import UUID
from pydantic import BaseModel


class AnswerBase(BaseModel):
    text: Optional[Dict[str, Any]]   
    main_question_id: Optional[UUID] = None
    sub_question_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


@optional()
class AnswerUpdate(AnswerBase):
    id: UUID


class AnswerCreate(AnswerBase):
    pass


class ChildrenReadForAnswerRead(BaseModel):
    id: UUID
    parent_id: UUID
    text: Optional[Dict[str, Any]]
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class ParentReadForAnswerRead(BaseModel):
    id: UUID
    text: Optional[Dict[str, Any]]
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: Optional[bool] = False
    children: Optional[List[ChildrenReadForAnswerRead]] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class AnswerRead(AnswerBase):
    id: UUID
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    auto_answer: bool = False
    parent: Optional[ParentReadForAnswerRead] = None
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


# Handle forward references for self-referential models
AnswerRead.model_rebuild(force=True)
