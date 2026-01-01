from typing import Optional, Any
from uuid import UUID
import uuid
from pydantic import BaseModel, Field, model_validator

# Mocking the structure to reproduce the behavior
class QuestionBase(BaseModel):
    items: dict = {}

class Question(QuestionBase):
    slug: Optional[str] = Field(default=None)
    
    # Defined AFTER slug
    exam_paper_id: UUID | None = Field(default=None)
    
    @model_validator(mode="before")
    @classmethod
    def set_slug(cls, data: Any) -> Any:
        print(f"DEBUG: data type: {type(data)}")
        if isinstance(data, dict):
            print(f"DEBUG: data keys inside model_validator: {list(data.keys())}")
            exam_paper_id = data.get("exam_paper_id")
            print(f"DEBUG: exam_paper_id found: {exam_paper_id}")
            
            if data.get("slug"):
                return data
                
            slug = "test-slug"
            if exam_paper_id:
                slug = f"{slug}-{str(exam_paper_id)[:6]}"
            
            data["slug"] = slug
        return data

# Test it
try:
    print("Creating Question...")
    ep_id = uuid.uuid4()
    q = Question(exam_paper_id=ep_id)
    print(f"Resulting Slug: {q.slug}")
    
    expected_slug = f"test-slug-{str(ep_id)[:6]}"
    if q.slug == expected_slug:
         print("✅ SUCCESS: Slug generated correctly with exam_paper_id")
    else:
         print(f"❌ FAILURE: expected {expected_slug}, got {q.slug}")

except Exception as e:
    print(f"Error: {e}")
