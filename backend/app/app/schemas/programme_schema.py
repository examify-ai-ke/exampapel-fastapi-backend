from typing import  Optional
from app.models.programme_model import ProgrammeBase
# from app.models.team_model import TeamBase
from app.utils.partial import optional
from uuid import UUID
from app.schemas.course_schema import CourseRead
from pydantic import  BaseModel


class ProgrammeCreate(ProgrammeBase):
    pass  # No extra fields required for creating a programme


@optional()
class ProgrammeUpdate(ProgrammeBase):
    # name: Optional[str]
    # description: Optional[str]
    # slug: Optional[str]
    # image: Optional[str]
    pass

class DepartmentReadForProgrammeRead(BaseModel):
    id:UUID
    name:str
    # slug: str
    faculty_id: Optional[UUID]
    class Config:
        from_attributes = True 
class ProgrammeRead(ProgrammeBase):
    id: UUID  # ID is known after creation
    # slug: str
    departments: list[DepartmentReadForProgrammeRead] | None = []
    courses: list[CourseRead] | None = [] 

    class Config:
        from_attributes = True  # This allows the schema to work with ORM objects
