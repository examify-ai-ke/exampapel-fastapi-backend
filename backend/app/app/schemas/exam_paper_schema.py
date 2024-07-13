from datetime import datetime
from typing import List, Optional, Dict, Any

from app.utils.partial import optional
from uuid import UUID
from app.models.exam_paper_model import ExamPaperBase, ExamTitleBase
from pydantic import field_validator, BaseModel

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


@optional()
class ExamPaperUpdate(ExamPaperBase):
    # slug: Optional[str]
    # name: Optional[str]
    # description: Optional[str]
    # slug: Optional[str]
    # logo: Optional[str]
    # institution_type: Optional[InstitutionTypeEnum]
    pass

class ModuleReadForExamPaper(BaseModel):
    id: UUID
    name: str
    slug: str
    unit_code: str

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
    # id:UUID
    name:str
    # slug: str
class CourseReadForExamPaper(BaseModel):
    # id:UUID
    name:str
    slug:str
# Schema for reading a ExamPaper
class ExamPaperRead(ExamPaperBase):
    id: UUID
    tags: Optional[List] 
    instructions: Optional[List[InstructionRead]]   = []  # To represent the relationship
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
    exam_date: datetime

class ExamTitleReadForExamPaperRead(BaseModel):
    id: UUID
    name: str
    slug: str
    
    
# ExamDescription
# ------------------------------------------------------------------------
class ExamDescriptionCreate(BaseModel):
    name: str
    description: Optional[str] = (
        "The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For...."
    )


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
