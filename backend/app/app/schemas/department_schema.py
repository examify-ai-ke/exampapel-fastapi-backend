from typing import List, Optional

from app.utils.partial import optional
from uuid import UUID
# from app.schemas.institution_schema import InstitutionDepartmentBase
from pydantic import field_validator, BaseModel

# Faculty Schemas
class DepartmentBase(BaseModel):
    name: str
    description: Optional[str]
    slug: Optional[str]


# Create schema for Department
class DepartmentCreate(DepartmentBase):  
    faculty_id: UUID # Needed to create a Department in a specific Faculty

class ProgrammeReadForDepartments(BaseModel):
    id: UUID
    name: str
    slug: str
    class Config:
        from_attributes = True


# Read schema for Department
class DepartmentRead(DepartmentBase):
    id: Optional[UUID] # Read schema includes the unique identifier
    faculty_id: Optional[UUID]   # Read schema has faculty reference
    programmes: Optional[List[ProgrammeReadForDepartments]]
    class Config:
        from_attributes = True


class DepartmentReadForFaculty(BaseModel):
    id: Optional[UUID]  # Read schema includes the unique identifier
    name: str
    slug:Optional[str]
    programmes: Optional[List[ProgrammeReadForDepartments]]
    class Config:
        from_attributes = True


# Update schema for Department
class DepartmentUpdate(BaseModel):
    name: Optional[str]  # Optional fields for updating
    description: Optional[str]
    slug:Optional[str]
