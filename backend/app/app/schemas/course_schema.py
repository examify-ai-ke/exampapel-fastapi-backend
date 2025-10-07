from typing import List, Optional
from app.utils.partial import optional
from uuid import UUID
from app.schemas.image_media_schema import IImageMediaRead

from app.schemas.exam_paper_schema import ExamPaperRead
from pydantic import   BaseModel


# Base schema for Course
class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    course_acronym: Optional[str] = None


@optional()
class CourseUpdate(CourseBase):
    faculty_id: Optional[UUID] = None
    pass


# Schema for creating a Course
class CourseCreate(CourseBase):
    programme_id: UUID  # Required to create a course within a programme
    faculty_id: Optional[UUID] = None  # Optional faculty association
    pass


class ModuleReadForCourse(BaseModel):
    id:UUID
    name:str
    # slug: str
    unit_code:str
    class Config:
        from_attributes = True 


class ExamTitleRead(BaseModel):
    id: UUID
    name: str
    # slug: str

    class Config:
        from_attributes = True  #


class ExamDescriptionReadForExamPaper(BaseModel):
    id: UUID
    name: str
    # slug: str

    class Config:
        from_attributes = True


class ExamPapersReadForCourse(BaseModel):
    id:UUID
    title:  Optional[ExamTitleRead] =None
    description: Optional[ExamDescriptionReadForExamPaper]=None
    class Config:
        from_attributes = True 

class FacultyReadForDepartment(BaseModel):
    id: Optional[UUID]
    name: Optional[str]

    class Config:
        from_attributes = True


class InstitutionReadForFaculty(BaseModel):
    id: UUID
    name: str
    slug: str
    class Config:
        from_attributes = True


class FacultyReadForCourse(BaseModel):
    id: Optional[UUID]
    name: Optional[str]
    institutions: Optional[list[InstitutionReadForFaculty]] = []
    class Config:
        from_attributes = True


class DepartmentReadForProgrammeCourse(BaseModel):
    id: Optional[UUID]
    faculty: Optional[FacultyReadForDepartment]
    class Config:
        from_attributes = True


class ProgrammeReadForCourse(BaseModel):

    id: Optional[UUID]  # ID is known after creation
    name: Optional[str]  = None
    
    class Config:
        from_attributes = True


# Schema for reading a Course
class CourseRead(CourseBase):
    id: UUID
    # slug:str
    course_acronym: str | None
    programme: ProgrammeReadForCourse
    faculty: Optional[FacultyReadForCourse] = None
    modules: Optional[list[ModuleReadForCourse]]
    exam_papers: Optional[List[ExamPapersReadForCourse]]
    image: IImageMediaRead | None
    modules_count: int | None = 0
    exam_papers_count: int | None = 0

    class Config:
        from_attributes = True  # Allows the schema to work with ORM objects
