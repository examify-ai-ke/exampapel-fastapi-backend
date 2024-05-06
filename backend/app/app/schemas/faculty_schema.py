from typing import List, Optional

# from app.schemas.institution_schema import InstitutionFacultyBase
from app.utils.partial import optional
from uuid import UUID
# from app.schemas.institution_schema import InstitutionDepartmentBase
from pydantic import field_validator, BaseModel

# Faculty Schemas
class FacultyBase(BaseModel):
    name: str
    description: Optional[str]
    slug: Optional[str]

class FacultyCreate(FacultyBase):
    pass


class FacultyRead(FacultyBase):
    id: UUID
    # courses: List[CourseRead]

    class Config:
        from_attributes = True


@optional()
class FacultyUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    slug: Optional[str]
    # institution_faculty: Optional[InstitutionFacultyBase]
