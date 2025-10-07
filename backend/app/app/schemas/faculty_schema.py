from typing import List, Optional

# from app.schemas.institution_schema import InstitutionFacultyBase
from app.utils.partial import optional
from uuid import UUID
# from app.schemas.institution_schema import InstitutionDepartmentBase
from app.schemas.department_schema import DepartmentReadForFaculty

# from app.models.institution_model import Institution
from pydantic import field_validator, BaseModel

# Faculty Schemas
class FacultyBase(BaseModel):
    name: str
    description: Optional[str]


class FacultyCreate(FacultyBase):
    # institutions: List[UUID] | None = []  # List of institution IDs to create a Faculty in specific institutions
    pass

class InstitutionForFaculty(BaseModel):
    slug: str
    name: str
    id :UUID
    class Config:
        from_attributes = True


class CourseReadForFaculty(BaseModel):
    id: UUID
    name: str
    course_acronym: Optional[str]
    class Config:
        from_attributes = True


class FacultyRead(FacultyBase):
    id: UUID
    departments: list[DepartmentReadForFaculty] = []
    courses: list[CourseReadForFaculty] = []
    department_count: int = 0
    courses_count: int = 0
    institutions: list[InstitutionForFaculty] = []
    institution_count: int = 0

    class Config:
        from_attributes = True


@optional()
class FacultyUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    # slug: Optional[str]
    # institution_faculty: Optional[InstitutionFacultyBase]
