
import os
from uuid import uuid4
from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum

# Mocking enough pieces to test serialization without importing the whole app
class InstitutionCategory(str, Enum):
    UNIVERSITY = "University"

class InstitutionType(str, Enum):
    PUBLIC = "Public"

class IMediaRead(BaseModel):
    id: Any
    path: str
    link: Optional[str] = None

class IImageMediaRead(BaseModel):
    media: Optional[IMediaRead]

class AddressRead(BaseModel):
    id: Any
    address_line1: str
    country: str

class InstitutionRead(BaseModel):
    id: Any
    name: str
    logo: Optional[IImageMediaRead] = None
    address: Optional[AddressRead] = None

def test_manual_serialization():
    print("Testing manual serialization with mock InstitutionRead schema...")
    
    data = {
        "id": uuid4(),
        "name": "Test University",
        "logo": {
            "media": {
                "id": uuid4(),
                "path": "test.png",
                "link": "http://example.com/test.png"
            }
        },
        "address": {
            "id": uuid4(),
            "address_line1": "123 Test St",
            "country": "Kenya"
        }
    }
    
    try:
        obj = InstitutionRead(**data)
        serialized = obj.model_dump()
        print(f"Serialized Logo: {serialized.get('logo')}")
        print(f"Serialized Address: {serialized.get('address')}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_manual_serialization()
