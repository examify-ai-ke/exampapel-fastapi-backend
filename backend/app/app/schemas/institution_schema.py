from typing import  Optional
from app.models.institution_model import InstitutionBase
# from app.models.team_model import TeamBase
from app.utils.partial import optional
from uuid import UUID

from app.schemas.campus_schema import CampusRead
from app.models.exam_paper_model import ExamPaperBase
from app.schemas.question_schema import QuestionSetRead
from pydantic import  BaseModel

from app.schemas.exam_paper_schema import CourseReadForExamPaper, ExamDescriptionReadForExamPaper,  ExamTitleReadForExamPaperRead,  InstructionRead, ModuleReadForExamPaper
from .image_media_schema import IImageMediaRead

class InstitutionCreate(InstitutionBase):
    pass
    # name: str = Field(nullable=False, unique=True)
    # description: Optional[str] = Field(nullable=True, default="An Institution of choice")
    # institution_type: InstitutionTypes = Field(
    #     sa_column=Column(Enum(InstitutionTypes), nullable=False))
    # email: EmailStr = Field(sa_column=Column(String, index=True, unique=True))
    # phone_number: Optional[str] = Field(nullable=False)
    # # pass  # No extra fields required for creating an institution


@optional()
class InstitutionUpdate(InstitutionBase):
    # name: Optional[str]
    # description: Optional[str]
    # slug: Optional[str]
    # logo: Optional[str]
    # institution_type: Optional[InstitutionTypeEnum]
    pass


# InstitutionFaculty Schemas
class InstitutionFacultyBase(BaseModel):
    name: str
    description: Optional[str]


class InstitutionFacultyCreate(InstitutionFacultyBase):
    pass

class DepartmentReadForFacultyReadForInstitution(BaseModel):
    name: str
    id: UUID
    slug: str
    class Config:
        from_attributes = True


class FacultyReadForInstitution(BaseModel):
    id: UUID
    name: str
    slug: str
    departments: list[DepartmentReadForFacultyReadForInstitution] | None = []
    class Config:
        from_attributes = True


class ExamPaperReadForInstitution(ExamPaperBase):
    id: UUID
    tags: Optional[list[str]] = []
    instructions: Optional[list[InstructionRead]] = []  # To represent the relationship
    title: ExamTitleReadForExamPaperRead = []
    description: ExamDescriptionReadForExamPaper
    modules: Optional[list[ModuleReadForExamPaper]] = []
    created_by_id: UUID
    # institution: InstitutionReadForExamPaper
    # hash_code: Optional[str]
    course: Optional[CourseReadForExamPaper]
    question_sets: Optional[list[QuestionSetRead]] = []

    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic


class InstitutionRead(InstitutionBase):
    id: UUID  # ID is known after creation
    faculties: list[FacultyReadForInstitution] | None = []
    campuses: list[CampusRead] | None = []
    exam_papers: list[ExamPaperReadForInstitution] | None = []
    exams_count: int | None = 0
    campuses_count: int | None =0
    faculties_count: int | None =0
    logo: IImageMediaRead | None = None
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