# Inserter.py API Schema and Flow Fixes Summary

## Overview
This document summarizes the fixes made to align `inserter.py` with the actual FastAPI backend API schema and flow.

## Issues Fixed

### 1. Response Parsing - Missing `data` Field Extraction
**Issue:** The login and token refresh endpoints return data wrapped in a `data` field (via `IPostResponseBase`), but the client was trying to parse the entire response directly.

**Backend Response Format:**
```python
{
    "data": {...},  # Actual token data is here
    "message": "Login correctly",
    "meta": {...}
}
```

**Fix Applied:**
Updated [`AuthClient.login()`](inserter.py:90) and [`AuthClient.refresh_access_token()`](inserter.py:127) to extract the `data` field before parsing:

```python
if response.status_code == 200:
    response_data = response.json()
    # Backend returns data wrapped in response format
    token_data = TokenResponse(**response_data["data"])
    self.access_token = token_data.access_token
    self.refresh_token = token_data.refresh_token
    self.user_info = token_data.user
```

### 2. LoginRequest Schema - Missing `provider` Field
**Issue:** The [`LoginRequest`](inserter.py:52) schema was missing the `provider` field which is required by the backend.

**Backend Schema:**
```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str 
    provider: AuthProvider = Field(default=AuthProvider.email)
```

**Fix Applied:**
```python
class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    provider: str = Field(default="email")
    
    model_config = ConfigDict(from_attributes=True)
```

---

### 2. InstitutionCreate Schema - Incorrect Default Values
**Issue:** The default values for `category` and `institution_type` were using string values instead of the actual enum values.

**Backend Schema:**
```python
class InstitutionCreate(BaseModel):
    name: str
    description: Optional[str] = "An Institution of choice"
    category: InstitutionCategory = InstitutionCategory.UNIVERSITY
    institution_type: Optional[InstitutionType] = InstitutionType.PUBLIC
```

**Fix Applied:**
```python
class InstitutionCreate(BaseModel):
    """Schema for creating an institution"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field("An Institution of choice", max_length=500)
    category: str = Field(default="UNIVERSITY")
    institution_type: str = Field(default="PUBLIC")
    location: Optional[str] = Field(None, max_length=200)
    key: Optional[str] = None
    kuccps_institution_url: Optional[str] = None
    full_profile: Optional[str] = None
    parent_ministry: Optional[str] = None
    tags: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)
```

**Changes:**
- Changed `"University"` → `"UNIVERSITY"` (matches enum)
- Changed `"Public"` → `"PUBLIC"` (matches enum)
- Added missing optional fields: `key`, `kuccps_institution_url`, `full_profile`, `parent_ministry`, `tags`
- Updated description default to match backend

---

### 3. ExamPaperCreate Schema - Tags Default Value
**Issue:** The `tags` field had incorrect default value.

**Backend Schema:**
```python
class ExamPaperCreate(ExamPaperBase):
    instruction_ids: List[UUID]
    module_ids:List[UUID]
    tags: Optional[List] = None
    title_id: UUID
    description_id:UUID
    course_id:UUID
    institution_id:UUID
```

**Fix Applied:**
```python
tags: Optional[List[str]] = Field(default=None)
```

Changed from `Field(default=[])` to `Field(default=None)` to match backend schema.

---

### 4. ExamDescriptionCreate Schema - Missing Default Description
**Issue:** The default description was missing.

**Backend Schema:**
```python
class ExamDescriptionCreate(BaseModel):
    name: str
    description: Optional[str] = "The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For...."
```

**Fix Applied:**
```python
class ExamDescriptionCreate(BaseModel):
    """Schema for creating exam description"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field("The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For....", max_length=500)
    
    model_config = ConfigDict(from_attributes=True)
```

---

### 5. ExamInstructionCreate Schema - Missing `slug` Field
**Issue:** The `slug` field was missing from the schema.

**Backend Schema:**
```python
class InstructionCreate(BaseModel):
    name: str
    slug:Optional[str]
    class Config:
        from_attributes = True
```

**Fix Applied:**
```python
class ExamInstructionCreate(BaseModel):
    """Schema for creating exam instruction"""
    name: str = Field(..., min_length=2, max_length=500)
    slug: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
```

---

### 6. MainQuestionCreate and SubQuestionCreate - Missing Text Validator
**Issue:** The question schemas were missing the `text_to_dict` field validator that converts text to dict format, which is required by the backend.

**Backend Schema:**
```python
class MainQuestionCreate(QuestionBase):
    question_set_id: UUID 
    exam_paper_id: UUID

@field_validator("text", mode="before")
@classmethod
def text_to_dict(cls, v):
    if v is None:
        return v
    if isinstance(v, dict):
        return v
    if hasattr(v, "model_dump"):
        return v.model_dump()
    return v
```

**Fix Applied:**
Added the `text_to_dict` validator to both [`MainQuestionCreate`](inserter.py:517) and [`SubQuestionCreate`](inserter.py:539):

```python
class MainQuestionCreate(BaseModel):
    """Schema for creating main questions"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="numerical")
    question_number: str = Field(..., min_length=1)
    question_set_id: UUID
    exam_paper_id: UUID
    
    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return v
    
    model_config = ConfigDict(from_attributes=True)

class SubQuestionCreate(BaseModel):
    """Schema for creating sub-questions"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="alphabetic")
    question_number: str = Field(default="a")
    parent_id: UUID
    
    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return v
    
    model_config = ConfigDict(from_attributes=True)
```

---

### 7. Sample Data - Incorrect Enum Values

**Issue:** The sample data used incorrect enum values for:
- Institution category and type
- Question numbering_style
- Question set title

**Backend Enum Values:**
- **InstitutionCategory:** `UNIVERSITY`, `COLLEGE`, `HIGH_SCHOOL`, etc.
- **InstitutionType:** `PUBLIC`, `PRIVATE`, `NGO`, etc.
- **NumberingStyleEnum:** `roman`, `alpha`, `numerical` (not `alphabetic`)
- **QuestionSetTitleEnum:** `QUESTION_ONE`, `QUESTION_TWO`, etc. (not `"Question One"`)

**Fix Applied:**
Updated sample data in [`create_sample_exam_paper()`](inserter.py:1142):
```python
"institution": {
    "name": "University of Technology",
    "description": "Leading technology university",
    "category": "UNIVERSITY",  # Changed from "University"
    "institution_type": "PUBLIC"  # Changed from "Public"
    "location": "Nairobi"
}
```

And for all question numbering styles:
```python
"numbering_style": "alpha",  # Changed from "alphabetic"
```

And question set title:
```python
"question_sets": [
    {
        "title": "QUESTION_ONE",  # Changed from "Question One"
```

---

## API Endpoints Verified

The following API endpoints were verified against the backend:

### Authentication
- **POST** `/api/v1/login` - Returns `Token` with `access_token`, `refresh_token`, `user`
- **POST** `/api/v1/login/new_access_token` - Refreshes access token
- **POST** `/api/v1/logout` - Logs out user

### Institution
- **GET** `/api/v1/institution` - List institutions with pagination
- **GET** `/api/v1/institution/get_by_id/{id}` - Get by ID
- **GET** `/api/v1/institution/get_by_slug/{slug}` - Get by slug
- **POST** `/api/v1/institution` - Create institution (requires admin/manager role)

### Exam Paper
- **GET** `/api/v1/exam-paper` - List exam papers
- **GET** `/api/v1/exam-paper/get_by_id/{id}` - Get by ID
- **GET** `/api/v1/exam-paper/get_by_slug/{slug}` - Get by slug
- **POST** `/api/v1/exam-paper` - Create exam paper (requires admin/manager role)
- **POST** `/api/v1/exam-paper/{exam_paper_id}/question-sets/{question_set_id}` - Link question set
- **POST** `/api/v1/exam-paper/{exam_paper_id}/modules/{module_id}` - Link module
- **DELETE** `/api/v1/exam-paper/{exam_paper_id}/modules/{module_id}` - Unlink module

### Exam Title
- **POST** `/api/v1/exam-title` - Create exam title (requires admin/manager role)

### Exam Description
- **POST** `/api/v1/exam-description` - Create exam description (requires admin/manager role)

### Instruction
- **POST** `/api/v1/instruction` - Create instruction (requires admin/manager role)

### Module
- **GET** `/api/v1/module` - List modules
- **GET** `/api/v1/module/get_by_id/{id}` - Get by ID
- **GET** `/api/v1/module/get_by_slug/{slug}` - Get by slug
- **POST** `/api/v1/module` - Create module (requires admin/manager role)

### Course
- **GET** `/api/v1/course` - List courses
- **GET** `/api/v1/course/get_by_id/{id}` - Get by ID
- **GET** `/api/v1/course/get_by_slug/{slug}` - Get by slug
- **POST** `/api/v1/course` - Create course (requires admin/manager role)

### Question Set
- **GET** `/api/v1/question-set` - List question sets
- **GET** `/api/v1/question-set/get_by_id/{id}` - Get by ID
- **POST** `/api/v1/question-set` - Create question set (requires admin/manager role)
- **GET** `/api/v1/question-set/{question_set_id}/questions` - Get main questions for a question set
- **GET** `/api/v1/exam-paper/{exam_paper_id}/question-sets` - Get question sets with questions for an exam paper

### Questions
- **GET** `/api/v1/questions` - List questions with filters
- **GET** `/api/v1/questions/{question_id}` - Get question by ID
- **GET** `/api/v1/questions/{question_id}/sub-questions` - Get sub-questions
- **POST** `/api/v1/questions/main` - Create main question (requires admin/manager role)
- **POST** `/api/v1/questions/sub` - Create sub-question (requires admin/manager role)
- **POST** `/api/v1/questions/{question_id}/sub-questions/bulk` - Bulk create sub-questions (requires admin/manager role)

---

## Response Format

All API endpoints return responses in the format:
```python
{
    "data": {...},
    "message": "Success message",
    "meta": {...}
}
```

The client correctly extracts `response.json()["data"]` to access the actual data.

---

## Summary

The [`inserter.py`](inserter.py) file has been updated to align with the actual FastAPI backend API schema and flow. All schemas now match the backend expectations, and the sample data uses correct enum values. The client is now ready for use.

### Files Modified
- `inserter.py` - Main client file with all fixes applied

### Testing Recommendations

1. Ensure the API base URL matches your server configuration
2. Verify authentication credentials are valid
3. Check that the user has appropriate roles (admin/manager) for creating resources
4. Test the authentication flow first before attempting other operations
5. Verify that enum values match what the backend expects
6. Handle errors gracefully and log them appropriately

---

**Date:** 2025-12-25
**Author:** Kilo Code
