from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Reuse existing schemas where possible, or define new ones similar to inserter.py

# --- Prerequisites Schemas ---

class BuilderExamTitleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)

class BuilderExamDescriptionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)

class BuilderProgrammeCreate(BaseModel):
    name: str
    description: Optional[str] = None

class BuilderCourseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    course_acronym: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    # Programme is nested in prerequisites, so we handle the link manually

class BuilderInstitutionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category: str = Field(default="University")
    institution_type: str = Field(default="Public")
    location: Optional[str] = None

class BuilderModuleCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    unit_code: Optional[str] = None
    description: Optional[str] = None

class BuilderInstructionCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=500)

class PrerequisitesCreate(BaseModel):
    exam_title: Optional[BuilderExamTitleCreate] = None
    exam_description: Optional[BuilderExamDescriptionCreate] = None
    course: Optional[BuilderCourseCreate] = None
    institution: Optional[BuilderInstitutionCreate] = None
    programme: Optional[BuilderProgrammeCreate] = None
    modules: List[BuilderModuleCreate] = []
    instructions: List[BuilderInstructionCreate] = []

# --- Question Schemas ---

class EditorJSBlock(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]

class QuestionTextSchema(BaseModel):
    time: int
    blocks: List[EditorJSBlock]

class BuilderSubQuestionCreate(BaseModel):
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = None
    numbering_style: str = "alphabetic"
    question_number: str = "a"

    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump(mode='json')
        return v

class BuilderMainQuestionCreate(BaseModel):
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = None
    numbering_style: str = "numeric"
    question_number: str
    sub_questions: List[BuilderSubQuestionCreate] = []

    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump(mode='json')
        return v

class BuilderQuestionSetCreate(BaseModel):
    title: str
    main_questions: List[BuilderMainQuestionCreate] = []

class QuestionsCreate(BaseModel):
    question_sets: List[BuilderQuestionSetCreate] = []

# --- Exam Paper Schema ---

class BuilderExamPaperCreate(BaseModel):
    year_of_exam: str
    exam_duration: int
    exam_date: Optional[date] = None
    tags: Optional[List[str]] = None

    @field_validator('year_of_exam')
    @classmethod
    def validate_year_format(cls, v):
        if not v or '/' not in v:
            raise ValueError('Year must be in format YYYY/YYYY')
        return v

# --- Top Level Schema ---

class CompleteExamPaperCreate(BaseModel):
    exam_paper: BuilderExamPaperCreate
    prerequisites: PrerequisitesCreate
    questions: QuestionsCreate
