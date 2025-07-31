from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.schemas.address_schema import AddressRead, AddressCreate, AddressUpdate


# Campus Schemas
class CampusBase(BaseModel):
    name: str
    description: Optional[str]
    slug: Optional[str]


class CampusCreate(BaseModel):
    name: str
    description: Optional[str]
    institution_id: UUID  # Foreign key for creating a campus
    address: Optional[AddressCreate] = None


class CampusRead(CampusBase):
    id: UUID
    address: Optional[AddressRead] = None
     
    # institution_id: UUID  # Reference to which institution this campus belongs to

    class Config:
        from_attributes = True


class CampusUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    address: Optional[AddressUpdate] = None
