from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia

from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug


# Define the Campus model
class CampusBase(SQLModel):  
    name: str = Field(nullable=False)
    location: Optional[str] = None
    slug: Optional[str] = Field(default=None, unique=True)

class Campus(BaseUUIDModel,CampusBase, table=True):    
    # Foreign key to Institution
    institution_id: UUID = Field(foreign_key="Institution.id", nullable=False)
    
    # Relationships
    institution: "Institution" = Relationship(back_populates="campuses")
    
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Campus.created_by_id==User.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)
    