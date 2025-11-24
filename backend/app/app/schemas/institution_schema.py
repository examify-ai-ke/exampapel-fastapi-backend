from typing import  Optional
from app.models.institution_model import InstitutionBase, InstitutionType, InstitutionCategory
# from app.models.team_model import TeamBase
from app.utils.partial import optional
from uuid import UUID

from app.schemas.campus_schema import CampusRead
from app.models.exam_paper_model import ExamPaperBase
from app.schemas.question_schema import QuestionSetRead
from pydantic import  BaseModel, EmailStr

from app.schemas.exam_paper_schema import CourseReadForExamPaper, ExamDescriptionReadForExamPaper,  ExamTitleReadForExamPaperRead,  InstructionRead, ModuleReadForExamPaper
from .image_media_schema import IImageMediaRead
from .address_schema import AddressRead, AddressCreate, AddressUpdate

# Institution Schemas
class InstitutionCreate(BaseModel):
    name: str
    description: Optional[str] = "An Institution of choice"
    category: InstitutionCategory = InstitutionCategory.UNIVERSITY
    
    # Optional fields
    key: Optional[str] = None
    location: Optional[str] = None
    kuccps_institution_url: Optional[str] = None
    institution_type: Optional[InstitutionType] = InstitutionType.PUBLIC
    full_profile: Optional[str] = None
    parent_ministry: Optional[str] = None
    image_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    # Address relationship
    address: Optional[AddressCreate] = None


@optional()
class InstitutionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[InstitutionCategory] = None

    # Optional fields
    key: Optional[str] = None
    location: Optional[str] = None
    kuccps_institution_url: Optional[str] = None
    institution_type: Optional[InstitutionType] = None
    full_profile: Optional[str] = None
    parent_ministry: Optional[str] = None
    image_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    # Address relationship
    address: Optional[AddressUpdate] = None


# InstitutionFaculty Schemas
class InstitutionFacultyBase(BaseModel):
    name: str
    description: Optional[str]


class InstitutionFacultyCreate(InstitutionFacultyBase):
    pass

class DepartmentReadForFacultyReadForInstitution(BaseModel):
    name: str
    id: UUID
    # slug: str
    class Config:
        from_attributes = True


class FacultyReadForInstitution(BaseModel):
    id: UUID
    name: str
    # slug: str
    departments: list[DepartmentReadForFacultyReadForInstitution] | None = []
    class Config:
        from_attributes = True


class QuestionSetReadForExamPaperReadForInstitution(BaseModel):
    # id: UUID
    slug: Optional[str] = None
    # questions: Optional[List[QuestionReadForQuestionSet]] = []  # Main questions only
    questions_count: Optional[int] = 0
    # created_at: datetime

    class Config:
        from_attributes = True


class ExamPaperReadForInstitution(ExamPaperBase):
    id: UUID
    slug: Optional[str] = None
    hash_code: Optional[str] = None
    identifying_name: Optional[str] = None
    tags: Optional[list[str]] = []
    instructions: Optional[list[InstructionRead]] = []  # To represent the relationship
    title: Optional[ExamTitleReadForExamPaperRead] = None  # To represent the relationship
    description: Optional[ExamDescriptionReadForExamPaper] = None  # To represent the relationship
    modules: Optional[list[ModuleReadForExamPaper]] = []
    created_by_id: UUID
    course: Optional[CourseReadForExamPaper] = None
    question_sets: Optional[list[QuestionSetReadForExamPaperReadForInstitution]] = []
    questions_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic


class InstitutionRead(InstitutionBase):
    id: UUID  # ID is known after creation
    slug: str
    faculties: list[FacultyReadForInstitution] | None = []
    campuses: list[CampusRead] | None = []
    exam_papers: list[ExamPaperReadForInstitution] | None = []
    exams_count: int | None = 0
    campuses_count: int | None =0
    faculties_count: int | None =0
    # logo: IImageMediaRead | None = None
    # address: Optional[AddressRead] = None
    category: InstitutionCategory
    # institution_type: Optional[InstitutionType] = None
    key: Optional[str] = None
    kuccps_institution_url: Optional[str] = None
    full_profile: Optional[str] = None
    parent_ministry: Optional[str] = None
    tags: Optional[list[str]] = []
    class Config:
        from_attributes = True  # This allows the schema to work with ORM objects


class InstitutionDetailedStatistics(BaseModel):
    total_institutions:int
    total_courses: int
    total_departments: int
    total_modules: int
    total_faculties: int
    total_main_questions: int
    total_users: int
    total_exam_papers: int
    total_answers: int
    total_campuses: int
    class Config:
        from_attributes = True  
