from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.partial import optional
from uuid import UUID
from app.models.question_model import QuestionSetBase, NumberingStyleEnum
from app.schemas.answer_schema import AnswerRead
from pydantic import field_validator, BaseModel, Field


class BlockData(BaseModel):
    text: str

class Block(BaseModel):
    id: str
    data: Dict[str, Any]
    type: str

class QuestionTextSchema(BaseModel):
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

# Unified Question schemas
class QuestionBase(BaseModel):
    text: Optional[QuestionTextSchema]
    marks: Optional[int] = None
    numbering_style: NumberingStyleEnum
    question_number: str

    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return v

# For creating main questions
class MainQuestionCreate(QuestionBase):
    question_set_id: UUID 
    exam_paper_id: UUID

# For creating sub-questions
class SubQuestionCreate(QuestionBase):
    parent_id: UUID  # References the main question

# For updating questions
@optional()
class MainQuestionUpdate(QuestionBase):
    question_set_id: Optional[UUID] = None
    exam_paper_id: Optional[UUID] = None

@optional()
class SubQuestionUpdate(QuestionBase):
    parent_id: Optional[UUID] = None

# Main Question Read schema
class QuestionRead(QuestionBase):
    id: UUID
    slug: Optional[str] = None
    marks: int | None
    created_at: datetime
    
    # For main questions
    question_set_id: Optional[UUID] = None
    exam_paper_id: Optional[UUID] = None
    
    # For sub-questions
    parent_id: Optional[UUID] = None
    
    # Relationships
    children: Optional[List["QuestionRead"]] = []  # Sub-questions
    answers: Optional[List[AnswerRead]] = []
    
    # Helper properties (computed from model)
    is_main_question: Optional[bool]=False
    is_sub_question:  Optional[bool]=False

    class Config:
        from_attributes = True

# Update the forward reference
QuestionRead.model_rebuild()

# Specific read schemas for different contexts
class MainQuestionRead(QuestionRead):
    """Schema for main questions with required fields"""
    question_set_id: UUID  # Required for main questions
    exam_paper_id: UUID    # Required for main questions
    children: Optional[List[QuestionRead]] = []  # Sub-questions
    
    class Config:
        from_attributes = True

class SubQuestionRead(QuestionRead):
    """Schema for sub-questions with required fields"""
    parent_id: UUID  # Required for sub-questions
    
    class Config:
        from_attributes = True

# For use in QuestionSet responses
class QuestionReadForQuestionSet(QuestionBase):
    id: UUID
    slug: Optional[str] = None
    marks: int | None
    answers: Optional[List[AnswerRead]] = []
    children: Optional[List[QuestionRead]] = []  # Sub-questions

    class Config:
        from_attributes = True

# ---------------------------QuestionSet ------------------------

class QuestionSetCreate(QuestionSetBase):
    pass

@optional()
class QuestionSetUpdate(QuestionSetBase):
    pass

class QuestionSetRead(QuestionSetBase):
    id: UUID
    slug: Optional[str] = None
    questions: Optional[List[QuestionReadForQuestionSet]] = []  # Main questions only
    questions_count: Optional[int] = 0
    # created_at: datetime
    
    class Config:
        from_attributes = True
