from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.partial import optional
from uuid import UUID
from app.models.question_model import QuestionSetBase
from app.schemas.answer_schema import AnswerRead
from pydantic import field_validator, BaseModel


# class AnswerRead(BaseModel):
#     id: UUID
#     text: Optional[Dict[str, Any]]


class SubQuestionBase(BaseModel):
    text: Optional[Dict[str, Any]]
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
    # text: Optional[str] = ""
    text: Optional[Dict[str, Any]]
    marks: Optional[int] =None
    numbering_style: str
    question_number: str


class MainQuestionCreate(MainQuestionBase):
    question_set_id:UUID 
    exam_paper_id:UUID
    pass

@optional()
class MainQuestionUpdate(MainQuestionBase):
    question_set_id: UUID
    exam_paper_id: UUID
    pass

class QuestionSetReadForMain(BaseModel):
    title:str
    id:UUID


class MainQuestionRead(MainQuestionBase):
    id: UUID
    slug:str
    marks:int | None
    question_set: Optional[QuestionSetReadForMain]
    subquestions: Optional[List[SubQuestionRead]] = []
    answers:Optional[list[AnswerRead]]= []
    # order_within_question_set: Optional[str]
   
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
    main_questions_count: int | None = 0
    # created_at: datetime
    class Config:
        from_attributes = True


# # Create schema for Department
# class DepartmentCreate(DepartmentBase):
#     faculty_id: UUID # Needed to create a Department in a specific Faculty

# class ProgrammeReadForDepartments(BaseModel):
#     id: UUID
#     name: str
#     slug: str
# # Read schema for Department
# class DepartmentRead(DepartmentBase):
#     id: Optional[UUID] # Read schema includes the unique identifier
#     faculty_id: Optional[UUID]   # Read schema has faculty reference
#     programmes: Optional[List[ProgrammeReadForDepartments]]
#     class Config:
#         from_attributes = True


# class DepartmentReadForFaculty(BaseModel):
#     id: Optional[UUID]  # Read schema includes the unique identifier
#     name: str
#     slug:Optional[str]
#     programmes: Optional[List[ProgrammeReadForDepartments]]


# # Update schema for Department
# class DepartmentUpdate(BaseModel):
#     name: Optional[str]  # Optional fields for updating
#     description: Optional[str]
#     slug:Optional[str]
