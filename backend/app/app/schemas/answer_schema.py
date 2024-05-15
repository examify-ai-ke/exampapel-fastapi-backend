from typing import List, Optional
from app.utils.partial import optional
from uuid import UUID
from pydantic import   BaseModel


class AnswerBase(BaseModel):
    text: str
    parent_id: Optional[UUID] = None
    main_question_id: Optional[UUID] = None
    sub_question_id: Optional[UUID] = None


@optional()
class AnswerUpdate(AnswerBase):
    pass


class AnswerCreate(AnswerBase):
    pass

class ChildrenReadForAnswerRead(BaseModel):
    id: Optional[UUID]
    text: Optional[str]
    likes: int | None = 0
    dislikes: int | None = 0
    reviewed: bool = False
    
    class Config:
        from_attributes = True


class ParentReadForAnswerRead(BaseModel):
    id: UUID
    text: Optional[str]


class AnswerRead(AnswerBase):
    id: UUID
    likes: int | None = 0
    dislikes: int | None = 0
    reviewed: bool = False
    auto_answer: bool = False
    parent: Optional[ParentReadForAnswerRead] = None
    children: Optional[List[ChildrenReadForAnswerRead]] = []

    class Config:
        from_attributes = True

AnswerRead.model_rebuild(force=True)
# Handle forward references for self-referential models
