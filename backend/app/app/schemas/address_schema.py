from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from app.utils.partial import optional

# Address Schemas
class AddressBase(BaseModel):
    address_line1: str  # Required field
    country: str  # Required field
    address_line2: Optional[str] = None
    county: Optional[str] = None
    constituency: Optional[str] = None
    zip_code: Optional[str] = None
    telephone: Optional[str] = None
    telephone2: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None


class AddressCreate(AddressBase):
    address_line1: str = "Main Address"
    country: str = "Kenya"


@optional()
class AddressUpdate(AddressBase):
    pass


class AddressRead(AddressBase):
    id: UUID

    class Config:
        from_attributes = True 