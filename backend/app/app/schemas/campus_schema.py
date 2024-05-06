from typing import List, Optional
 
from uuid import UUID
from pydantic import   BaseModel


# Campus Schemas
class CampusBase(BaseModel):
    name: str
    location: Optional[str]
    slug: Optional[str]

class CampusCreate(BaseModel):
    name: str
    location: Optional[str]
    institution_id: UUID  # Foreign key for creating a campus


class CampusRead(CampusBase):
    id: UUID
    institution_id: UUID  # Reference to which institution this campus belongs to

    class Config:
        from_attributes = True


class CampusUpdate(BaseModel):
    name: Optional[str]
    location: Optional[str]
