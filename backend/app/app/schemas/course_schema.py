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
    course_acronym: str | None


@optional()
class CourseUpdate(CourseBase):
    # name: Optional[str]
    # description: Optional[str]
    # slug: Optional[str]
    pass


# Schema for creating a Course
class CourseCreate(CourseBase):
    programme_id: UUID  # Required to create a course within a programme
    
    pass


class ModuleReadForCourse(BaseModel):
    id:UUID
    name:str
    slug: str
    unit_code:str


class ExamPapersReadForCourse(BaseModel):
    id:UUID
    # title: str
    # description: str


# Schema for reading a Course
class CourseRead(CourseBase):
    id: UUID
    slug:str
    course_acronym: str | None
    programme_id: UUID
    modules: Optional[list[ModuleReadForCourse]]
    exam_papers: Optional[List[ExamPapersReadForCourse]]
    image: IImageMediaRead | None

    class Config:
        from_attributes = True  # Allows the schema to work with ORM objects
