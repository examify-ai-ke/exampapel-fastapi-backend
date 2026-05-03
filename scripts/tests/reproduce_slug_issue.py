from typing import Optional
from uuid import UUID
import uuid
from pydantic import BaseModel, Field, validator

# Mocking the structure to reproduce the behavior
class QuestionBase(BaseModel):
    items: dict = {}

class Question(QuestionBase):
    slug: Optional[str] = Field(default=None)
    
    # Defined AFTER slug
    exam_paper_id: UUID | None = Field(default=None)
    
    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        print(f"DEBUG: values keys inside validator: {list(values.keys())}")
        exam_paper_id = values.get("exam_paper_id")
        print(f"DEBUG: exam_paper_id found: {exam_paper_id}")
        
        if value:
            return value
            
        slug = "test-slug"
        if exam_paper_id:
            slug = f"{slug}-{str(exam_paper_id)[:6]}"
        return slug

# Test it
try:
    print("Creating Question...")
    q = Question(exam_paper_id=uuid.uuid4())
    print(f"Resulting Slug: {q.slug}")
except Exception as e:
    print(e)
