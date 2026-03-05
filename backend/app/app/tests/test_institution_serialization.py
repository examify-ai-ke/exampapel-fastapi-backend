import os
# Mock environment variables for config initialization
os.environ["DATABASE_USER"] = "postgres"
os.environ["DATABASE_PASSWORD"] = "postgres"
os.environ["DATABASE_HOST"] = "localhost"
os.environ["DATABASE_NAME"] = "test"
os.environ["DATABASE_PORT"] = "5432"
os.environ["DATABASE_CELERY_NAME"] = "celery"
os.environ["SECRET_KEY"] = "secret"
os.environ["ENCRYPT_KEY"] = "TshgGacKPYrm35m89UqbRg46JAbUm2yRtxOCQFdqa3w=" # Valid key

import asyncio
from uuid import uuid4
from pydantic import TypeAdapter
from app.models.institution_model import Institution, Address, InstitutionCategory, InstitutionType
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from app.schemas.institution_schema import InstitutionRead

async def test_serialization():
    # Mock data
    inst_id = uuid4()
    logo_id = uuid4()
    media_id = uuid4()
    address_id = uuid4()

    # Create mock models
    mock_media = Media(id=media_id, path="sample/path.png", title="Logo")
    mock_logo = ImageMedia(id=logo_id, media=mock_media, media_id=media_id, height=100, width=100)
    
    mock_address = Address(
        id=address_id,
        address_line1="123 Test St",
        country="Kenya",
        institution_id=inst_id
    )

    mock_institution = Institution(
        id=inst_id,
        name="Test University",
        slug="test-university",
        category=InstitutionCategory.UNIVERSITY,
        institution_type=InstitutionType.PUBLIC,
        logo=mock_logo,
        address=mock_address,
        exam_papers=[],
        campuses=[],
        faculties=[]
    )

    print("Testing serialization for InstitutionRead...")
    
    # Try serialization
    try:
        # Pydantic v2 style
        read_schema = InstitutionRead.model_validate(mock_institution)
        json_data = read_schema.model_dump()
        
        print("\nSerialized Data:")
        print(f"Name: {json_data.get('name')}")
        print(f"Logo present: {'logo' in json_data and json_data['logo'] is not None}")
        if json_data.get('logo'):
            print(f"Logo media link: {json_data['logo'].get('media', {}).get('link')}")
        
        print(f"Address present: {'address' in json_data and json_data['address'] is not None}")
        if json_data.get('address'):
            print(f"Address line 1: {json_data['address'].get('address_line1')}")
            
    except Exception as e:
        print(f"Serialization failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_serialization())
