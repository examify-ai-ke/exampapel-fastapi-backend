from typing import List, Optional

from app.utils.partial import optional
from uuid import UUID

from pydantic import field_validator, BaseModel

# Faculty Schemas
class ModuleBase(BaseModel):
    name: str
    description: Optional[str] = "An academic module/unit that forms part of the course"
    unit_code: str


@optional()
class ModuleUpdate(ModuleBase):
    slug: Optional[str]
    # name: Optional[str]
    # description: Optional[str]
    # slug: Optional[str]
    # logo: Optional[str]
    # institution_type: Optional[InstitutionTypeEnum]
    pass


# Schema for creating a Module
class ModuleCreate(ModuleBase):
    pass

class CourseReadForModule(BaseModel):
    id:UUID
    name:str
    slug:str
class ExamPaperReadForModule(BaseModel):
    id: UUID
    slug:str
    name:str
# Schema for reading a Module
class ModuleRead(ModuleBase):
    id: UUID
    slug: Optional[str]
    courses: Optional[List[CourseReadForModule]] = []  # To represent the relationship
    exam_papers: Optional[List[ExamPaperReadForModule]] = []
    # exam_papers_count: int #TODO
    class Config:
        from_attributes = True  # Allows ORM-based data to be converted to Pydantic
