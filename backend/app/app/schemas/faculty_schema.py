from typing import List, Optional

# from app.schemas.institution_schema import InstitutionFacultyBase
from app.utils.partial import optional
from uuid import UUID
# from app.schemas.institution_schema import InstitutionDepartmentBase
from app.schemas.department_schema import DepartmentRead
# from app.models.institution_model import Institution
from pydantic import field_validator, BaseModel

# Faculty Schemas
class FacultyBase(BaseModel):
    name: str
    description: Optional[str]
    slug: Optional[str]

class FacultyCreate(FacultyBase):
    pass

class InstitutionForFaculty(BaseModel):
    slug: str
    name: str
    id :UUID

class FacultyRead(FacultyBase):
    id: UUID
    department_count: int | None
    departments: list[DepartmentRead] | None =[]
    institution_count: int | None
    institutions: list[InstitutionForFaculty] | None =[]

    class Config:
        from_attributes = True

class DepartmentReadForFacultyReadForInstitution(BaseModel):
    name: str
    id :UUID
    slug: str
class FacultyReadForInstitution(BaseModel):
    id: UUID
    name: str
    slug: str
    departments: list[DepartmentReadForFacultyReadForInstitution] | None = []
    # department_count: int | None

@optional()
class FacultyUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    slug: Optional[str]
    # institution_faculty: Optional[InstitutionFacultyBase]
