from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String, Index
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional, TYPE_CHECKING

from app.models.image_media_model import ImageMedia

from pydantic import EmailStr, validator
from app.utils.slugify_string import generate_slug

if TYPE_CHECKING:
    from app.models.institution_model import Institution, Address


# Define the Campus model
class CampusBase(SQLModel):  
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default="An institution campus", unique=False)
    slug: Optional[str] = Field(default=None, unique=True)

class Campus(BaseUUIDModel,CampusBase, table=True):    
    # Foreign key to Institution
    institution_id: UUID = Field(foreign_key="Institution.id", nullable=False)

    # Relationships
    institution: "Institution" = Relationship(back_populates="campuses")

    # Address relationship
    address: Optional["Address"] = Relationship(
        back_populates="campus",
        sa_relationship_kwargs={
            "lazy": "joined"
        },
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Campus.created_by_id==User.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)
