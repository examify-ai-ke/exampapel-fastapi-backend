from datetime import date, datetime
from typing import List, Optional, Dict, Any

from app.utils.partial import optional
from uuid import UUID
from app.models.exam_paper_model import ExamInstruction, ExamPaperBase, ExamTitleBase
from app.models.module_model import Module
from pydantic import field_validator, ConfigDict, BaseModel

from app.schemas.answer_schema import AnswerReadForQuestion
from app.schemas.question_schema import QuestionBase, SubQuestionReadSimple
from app.schemas.image_media_schema import IImageMediaRead


# from  app.schemas.question_schema import QuestionSetRead


class ExamPaperCreate(ExamPaperBase):
    instruction_ids: List[UUID]
    module_ids:List[UUID]
    tags: Optional[List] = None
    title_id: UUID
    description_id:UUID
    course_id:UUID
    institution_id:UUID
    pass  # No extra fields required for creating an exampaper


# @optional()
# class ExamPaperUpdate(ExamPaperCreate):
#     # slug: Optional[str]
#     # name: Optional[str]
#     # description: Optional[str]
#     # slug: Optional[str]
#     # logo: Optional[str]
#     # institution_type: Optional[InstitutionTypeEnum]
#     pass


# Potential Update Schema

class ExamTitleUpdateNested(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None

class ExamDescriptionUpdateNested(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None

class ExamInstructionUpdateNested(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None

@optional()
class ExamPaperUpdate(BaseModel):
    title_id: Optional[UUID] = None
    description_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    exam_date: Optional[date] = None
    exam_duration: Optional[int] = None
    tags: Optional[List[str]] = None
    # Many-to-many relationships
    instruction_ids: Optional[List[UUID]] = None
    module_ids: Optional[List[UUID]] = None
    # Nested objects for inline editing
    title: Optional[ExamTitleUpdateNested] = None
    description: Optional[ExamDescriptionUpdateNested] = None
    instructions: Optional[List[ExamInstructionUpdateNested]] = None

    model_config = ConfigDict(json_encoders={UUID: str})


class ModuleReadForExamPaper(BaseModel):
    id: Optional[UUID] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    unit_code: Optional[str] = None
    class Config:
        from_attributes = True  #


class InstructionCreate(BaseModel):
    name: str
    slug:Optional[str]
    class Config:
        from_attributes = True

@optional()
class InstructionUpdate(BaseModel):
    name: str


class InstructionRead(BaseModel):
    id:UUID
    name: str
    slug:str
    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

class InstitutionReadForExamPaper(BaseModel):
    id:UUID
    name:str
    logo: IImageMediaRead | None = None

    class Config:
        from_attributes = True

class CourseReadForExamPaper(BaseModel):
    id:UUID
    name:str
    slug:Optional[str] = None
    class Config:
        from_attributes = True  #


class MainQuestionReadForQuestionSet(QuestionBase):
    id: UUID
    slug: Optional[str] = None
    marks: int | None
    # created_at: datetime
    # question_set_id: Optional[UUID] = None
    exam_paper_id: Optional[UUID] = None
    children: Optional[List[SubQuestionReadSimple]] = (
        []
    )  # Only one level of sub-questions
    answers: Optional[List[AnswerReadForQuestion]] = []

    class Config:
        from_attributes = True


class QuestionSetReadForExamPaperRead(BaseModel):
    id: UUID
    slug: Optional[str] = None
    title: Optional[str] = None
    questions_count: Optional[int] = 0
    questions: Optional[List[MainQuestionReadForQuestionSet]] = []
    # exam_papers_count: Optional[int] = 0
    # created_at: datetime

    class Config:
        from_attributes = True


# Schema for reading a ExamPaper
class ExamPaperRead(ExamPaperBase):
    id: UUID
    slug: Optional[str] = None
    tags: Optional[list[str]] = []
    instructions: Optional[list[InstructionRead]] = []  # To represent the relationship
    title: Optional["ExamTitleReadForExamPaperRead"] = None
    description: Optional["ExamDescriptionReadForExamPaper"] = None
    modules: Optional[List[ModuleReadForExamPaper]] = []
    created_by_id: UUID
    institution: InstitutionReadForExamPaper
    # hash_code: Optional[str]
    course:Optional[CourseReadForExamPaper]
    question_sets: Optional[List[QuestionSetReadForExamPaperRead]] = []
    questions_count: int = 0
    identifying_name: Optional[str]

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

# --------------------------------------------------------------

class ExamTitleCreate(ExamTitleBase):
    pass


@optional()
class ExamTitleUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    class Config:
        from_attributes = True


class ExamTitleRead(BaseModel):
    id: UUID
    name: str
    slug: str
    # exam_papers: Optional[List["ExamPaperReadForExamTitle"]] = None

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

class ExamPaperReadForExamTitle(BaseModel):
    id:UUID
    year_of_exam:str
    exam_date: date
    class Config:
        from_attributes = True
        # Allows ORM-based data to be converted to Pydantic

class ExamTitleReadForExamPaperRead(BaseModel):
    # id: UUID
    name: Optional[str]
    slug: Optional[str]
    class Config:
        from_attributes = True


# ExamDescription
# ------------------------------------------------------------------------
class ExamDescriptionCreate(BaseModel):
    name: str
    description: Optional[str] = (
        "The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For...."
    )
    class Config:
        from_attributes = True  #


@optional()
class ExamDescriptionUpdate(BaseModel):
    name: str
    desciption:str
    class Config:
        from_attributes = True


class ExamDescriptionRead(BaseModel):
    id: UUID
    name: str
    slug: str
    # exam_papers:Optional[List[ExamPaperReadForExamTitle]]

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

class ExamDescriptionReadForExamPaper(BaseModel):
    id: UUID
    name: str
    slug: str
    class Config:
        from_attributes = True
