from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.partial import optional
from uuid import UUID
from app.models.question_model import QuestionSetBase
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

class SubQuestionBase(BaseModel):
    text: Optional[QuestionTextSchema]
    marks: Optional[int] = None
    numbering_style: str
    question_number: str


class SubQuestionCreate(SubQuestionBase):
    main_question_id: UUID
    pass

@optional()
class SubQuestionUpdate(SubQuestionBase):
    main_question_id: UUID
    pass


class SubQuestionRead(SubQuestionBase):
    id: UUID
    main_question_id: UUID
    answers: Optional[list[AnswerRead]] = []

    class Config:
        from_attributes = True

# ------------------------------Main Question-----------
class MainQuestionBase(BaseModel):
    text: Optional[QuestionTextSchema]
    marks: Optional[int] = None
    numbering_style: str
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

class MainQuestionCreate(MainQuestionBase):
    question_set_id: UUID 
    exam_paper_id: UUID


@optional()
class MainQuestionUpdate(MainQuestionBase):
    question_set_id: UUID
    exam_paper_id: UUID


class QuestionSetReadForMain(BaseModel):
    title:str
    id:UUID


class MainQuestionRead(MainQuestionBase):
    id: UUID
    slug:str
    marks:int | None
    subquestions: Optional[List[SubQuestionRead]] = []
    answers:Optional[list[AnswerRead]]= []
    question_set_id: UUID
    exam_paper_id: UUID
    created_at: datetime
    # order_within_question_set: Optional[str]

    class Config:
        from_attributes = True


class MainQuestionReadForQuestionSet(MainQuestionBase):
    id: UUID
    slug: str
    marks: int | None
    answers: Optional[List[AnswerRead]] = []
    subquestions: Optional[List[SubQuestionRead]] = []

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
    slug:str
    main_questions: Optional[list[MainQuestionRead]] = []
    main_questions_count: Optional[int] = 0
    # created_at: datetime
    class Config:
        from_attributes = True
