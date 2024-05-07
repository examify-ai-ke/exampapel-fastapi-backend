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


# Read schema for Department
class DepartmentRead(DepartmentBase):
    id: Optional[UUID] # Read schema includes the unique identifier
    faculty_id: Optional[UUID]   # Read schema has faculty reference

    class Config:
        from_attributes = True


# Update schema for Department
class DepartmentUpdate(BaseModel):
    name: Optional[str]  # Optional fields for updating
    description: Optional[str]
    slug:Optional[str]
