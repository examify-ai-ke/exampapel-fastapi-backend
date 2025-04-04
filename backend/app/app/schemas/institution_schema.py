from typing import  Optional
from app.models.institution_model import InstitutionBase
# from app.models.team_model import TeamBase
from app.utils.partial import optional
from uuid import UUID
from app.schemas.faculty_schema import FacultyReadForInstitution 
from app.schemas.campus_schema import CampusRead
from pydantic import  BaseModel

from app.schemas.exam_paper_schema import ExamPaperRead
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


class InstitutionFacultyUpdate(BaseModel):
    name: Optional[str]
    description: str | None = []


class InstitutionRead(InstitutionBase):
    id: UUID  # ID is known after creation
    faculties: list[FacultyReadForInstitution] | None = []
    campuses: list[CampusRead] | None = []
    exam_papers: list[ExamPaperRead] | None = []
    exams_count: int | None = 0
    campuses_count: int | None =0
    faculties_count: int | None =0
    logo: IImageMediaRead | None = None
    class Config:
        from_attributes = True  # This allows the schema to work with ORM objects
