from datetime import date, datetime
from typing import List, Optional, Dict, Any

from app.utils.partial import optional
from uuid import UUID
from app.models.exam_paper_model import ExamInstruction, ExamPaperBase, ExamTitleBase
from app.models.module_model import Module
from pydantic import field_validator, ConfigDict, BaseModel


from  app.schemas.question_schema import QuestionSetRead


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

@optional()
class ExamPaperUpdate(BaseModel):
    title_id: Optional[UUID] = None
    description_id: Optional[UUID] = None
    course_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    exam_date: Optional[date] = None
    exam_duration: Optional[int] = None
    # tags: Optional[str[List]] = None
    tags: Optional[List[str]] = None
    # Many-to-many relationships
    instruction_ids: Optional[List[UUID]] =None
    module_ids: Optional[List[UUID]] = None

    # Other fields as needed

    # Ensure UUIDs can be validated
    model_config = ConfigDict(json_encoders={UUID: str})


class ModuleReadForExamPaper(BaseModel):
    id: UUID
    name: str
    slug: str
    unit_code: str
    class Config:
        from_attributes = True  #


class InstructionCreate(BaseModel):
    name: str
    slug:Optional[str]

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
    # slug: str
class CourseReadForExamPaper(BaseModel):
    id:UUID
    name:str
    slug:str
    class Config:
        from_attributes = True  #


# Schema for reading a ExamPaper
class ExamPaperRead(ExamPaperBase):
    id: UUID
    tags: Optional[List[str]] = []
    instructions: Optional[List[InstructionRead]] = []  # To represent the relationship
    title: "ExamTitleReadForExamPaperRead"   = []
    description: "ExamDescriptionReadForExamPaper"
    modules: Optional[List[ModuleReadForExamPaper]] = []
    created_by_id: UUID
    institution: InstitutionReadForExamPaper
    # hash_code: Optional[str]
    course:Optional[CourseReadForExamPaper]
    question_sets: Optional[List[QuestionSetRead]] = []

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

# --------------------------------------------------------------

class ExamTitleCreate(ExamTitleBase):
    pass


@optional()
class ExamTitleUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]


class ExamTitleRead(BaseModel):
    id: UUID
    name: str
    slug: str
    exam_papers: Optional[List["ExamPaperReadForExamTitle"]] = None

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

class ExamPaperReadForExamTitle(BaseModel):
    id:UUID
    year_of_exam:str
    exam_date: date

class ExamTitleReadForExamPaperRead(BaseModel):
    id: UUID
    name: str
    slug: str
    class Config:
        from_attributes = True  #


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


class ExamDescriptionRead(BaseModel):
    id: UUID
    name: str
    slug: str
    exam_papers:Optional[List[ExamPaperReadForExamTitle]]

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic

class ExamDescriptionReadForExamPaper(BaseModel):
    id: UUID
    name: str
    slug: str
    class Config:
        from_attributes = True
