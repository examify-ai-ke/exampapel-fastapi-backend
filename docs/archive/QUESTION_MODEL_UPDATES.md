# Question Model Updates Summary

## Overview
Updated the FastAPI backend to use a unified `Question` model instead of separate `MainQuestion` and `SubQuestion` models. This provides better flexibility and maintains the hierarchical relationship between main questions and sub-questions.

## Changes Made

### 1. Model Updates (`app/models/question_model.py`)
- ✅ **Already Updated**: The `Question` model now supports both main questions and sub-questions
- Main questions have: `question_set_id` and `exam_paper_id`
- Sub-questions have: `parent_id` (pointing to their main question)
- Added helper properties: `is_main_question` and `is_sub_question`
- Maintained backward compatibility with `MainQuestion = Question` and `SubQuestion = Question` aliases

### 2. Schema Updates (`app/schemas/question_schema.py`)
- ✅ **Updated**: Unified schemas to work with the new Question model
- `MainQuestionCreate`: For creating main questions (requires `question_set_id` and `exam_paper_id`)
- `SubQuestionCreate`: For creating sub-questions (requires `parent_id`)
- `MainQuestionUpdate` and `SubQuestionUpdate`: For updating respective question types
- `QuestionRead`: Base read schema with recursive relationship support
- `MainQuestionRead` and `SubQuestionRead`: Specialized read schemas
- Updated `QuestionSetRead` to use `questions` instead of `main_questions`

### 3. CRUD Updates
- ✅ **Updated**: `app/crud/main_question_crud.py` - Now uses unified `Question` model
- ✅ **Updated**: `app/crud/sub_question_crud.py` - Now uses unified `Question` model
- Added filtering logic to distinguish between main questions and sub-questions
- Added helper methods for querying specific question types

### 4. API Endpoint Updates

#### Main Question Endpoints (`app/api/v1/endpoints/main_question.py`)
- ✅ **Updated**: Now uses unified `Question` model
- Added filtering to ensure only main questions are returned
- Updated `selectinload` to use `Question.children` instead of `MainQuestion.subquestions`
- Added validation to ensure operations are performed on main questions only

#### Sub Question Endpoints (`app/api/v1/endpoints/sub_question.py`)
- ✅ **Updated**: Now uses unified `Question` model
- Added filtering to ensure only sub-questions are returned
- Added new endpoint: `GET /by_parent/{parent_question_id}` to get sub-questions by parent
- Added validation to ensure parent question exists and is a main question
- Added validation to ensure operations are performed on sub-questions only

#### Question Set Endpoints (`app/api/v1/endpoints/question_set.py`)
- ✅ **Updated**: Import changed from `MainQuestion` to `Question`
- Updated `selectinload` to use `Question.children` instead of `MainQuestion.subquestions`

## Key Features

### 1. Unified Model Benefits
- Single table for all questions reduces complexity
- Hierarchical relationship through self-referential foreign key
- Flexible structure allows for future extensions
- Maintains data integrity with proper constraints

### 2. Backward Compatibility
- Existing API endpoints continue to work
- Schema names remain the same
- CRUD operations maintain the same interface

### 3. Enhanced Functionality
- New endpoint to get sub-questions by parent ID
- Better relationship loading with proper `selectinload` usage
- Validation to ensure operations are performed on correct question types

### 4. Database Relationships
```
QuestionSet (1) -> (N) Question [main questions]
Question [main] (1) -> (N) Question [sub-questions] (parent_id)
ExamPaper (1) -> (N) Question [main questions]
Question (1) -> (N) Answer
```

## API Endpoints

### Main Questions
- `GET /main-questions` - List all main questions
- `GET /main-questions/get_by_id/{id}` - Get main question by ID
- `POST /main-questions` - Create new main question
- `PUT /main-questions/{id}` - Update main question
- `DELETE /main-questions/{id}` - Delete main question

### Sub Questions
- `GET /sub-questions` - List all sub-questions
- `GET /sub-questions/get_by_id/{id}` - Get sub-question by ID
- `GET /sub-questions/by_parent/{parent_id}` - Get sub-questions by parent ID (NEW)
- `POST /sub-questions` - Create new sub-question
- `PUT /sub-questions/{id}` - Update sub-question
- `DELETE /sub-questions/{id}` - Delete sub-question

### Question Sets
- `GET /question-sets` - List all question sets
- `GET /question-sets/get_by_id/{id}` - Get question set by ID (includes main questions and their sub-questions)
- `POST /question-sets` - Create new question set
- `PUT /question-sets/{id}` - Update question set
- `DELETE /question-sets/{id}` - Delete question set

## Migration Notes

### Database Migration Required
If you have existing data, you'll need to run Alembic migrations:
```bash
# Generate migration
make add-dev-migration

# Or manually:
docker compose -f docker-compose-dev.yml exec fastapi_server alembic revision --autogenerate
docker compose -f docker-compose-dev.yml exec fastapi_server alembic upgrade head
```

### Testing
- All endpoints should be tested to ensure they work with the new unified model
- Verify that main questions and sub-questions are properly filtered
- Test the new sub-question by parent endpoint
- Ensure proper relationship loading in responses

## Next Steps
1. Run database migrations
2. Test all endpoints with sample data
3. Update any frontend code that relies on the old field names
4. Consider adding more validation rules if needed
5. Update API documentation if necessary

## Files Modified
- `app/models/question_model.py` (already updated)
- `app/schemas/question_schema.py` ✅
- `app/crud/main_question_crud.py` ✅
- `app/crud/sub_question_crud.py` ✅
- `app/api/v1/endpoints/main_question.py` ✅
- `app/api/v1/endpoints/sub_question.py` ✅
- `app/api/v1/endpoints/question_set.py` ✅
