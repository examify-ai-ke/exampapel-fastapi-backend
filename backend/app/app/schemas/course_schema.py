from typing import List, Optional
from app.utils.partial import optional
from uuid import UUID
from pydantic import field_validator, BaseModel


# Base schema for Course
class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None


# Schema for creating a Course
class CourseCreate(CourseBase):
    programme_id: UUID  # Required to create a course within a programme


# Schema for reading a Course
class CourseRead(CourseBase):
    id: UUID
    programme_id: UUID

    class Config:
        from_attributes = True  # Allows the schema to work with ORM objects

