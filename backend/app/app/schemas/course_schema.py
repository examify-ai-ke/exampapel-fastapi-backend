from typing import List, Optional
from app.utils.partial import optional
from uuid import UUID
from app.schemas.image_media_schema import IImageMediaRead

from pydantic import field_validator, BaseModel


# Base schema for Course
class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None


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
# Schema for reading a Course
class CourseRead(CourseBase):
    id: UUID
    slug:str
    programme_id: UUID
    modules: Optional[list[ModuleReadForCourse]]
    image: IImageMediaRead | None

    class Config:
        from_attributes = True  # Allows the schema to work with ORM objects
