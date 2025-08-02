from typing import Any, Optional, Union
from uuid import UUID
from app.schemas.question_schema import (
    MainQuestionCreate, 
    SubQuestionCreate, 
    MainQuestionUpdate, 
    SubQuestionUpdate
)
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.question_model import Question
from sqlmodel import select, func, and_, col, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException


# Union types for flexibility
QuestionCreate = Union[MainQuestionCreate, SubQuestionCreate]
QuestionUpdate = Union[MainQuestionUpdate, SubQuestionUpdate]


class CRUDQuestion(CRUDBase[Question, QuestionCreate, QuestionUpdate]):
    """
    Unified CRUD operations for all question types (main and sub-questions)
    """

    async def create(
        self, 
        *, 
        obj_in: QuestionCreate, 
        created_by_id: UUID,
        db_session: AsyncSession | None = None
    ) -> Question:
        """
        Create a question (main or sub) with automatic type detection and validation
        """
        db_session = db_session or super().get_db().session
        
        # Validate based on question type
        if isinstance(obj_in, MainQuestionCreate):
            await self._validate_main_question_creation(obj_in, db_session)
        elif isinstance(obj_in, SubQuestionCreate):
            await self._validate_sub_question_creation(obj_in, db_session)
        
        return await super().create(
            obj_in=obj_in, 
            created_by_id=created_by_id, 
            db_session=db_session
        )

    async def update(
        self,
        *,
        obj_current: Question,
        obj_new: QuestionUpdate,
        db_session: AsyncSession | None = None
    ) -> Question:
        """
        Update a question with type-specific validation
        """
        db_session = db_session or super().get_db().session
        
        # Validate update based on current question type and new data
        if obj_current.is_main_question and isinstance(obj_new, MainQuestionUpdate):
            await self._validate_main_question_update(obj_current, obj_new, db_session)
        elif obj_current.is_sub_question and isinstance(obj_new, SubQuestionUpdate):
            await self._validate_sub_question_update(obj_current, obj_new, db_session)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update {self._get_question_type(obj_current)} question with {type(obj_new).__name__} schema"
            )
        
        return await super().update(
            obj_current=obj_current,
            obj_new=obj_new,
            db_session=db_session
        )

    # Query methods for different question types
    async def get_main_questions(
        self, 
        *,
        question_set_id: Optional[UUID] = None,
        exam_paper_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
        db_session: AsyncSession | None = None
    ) -> list[Question]:
        """Get all main questions with optional filtering"""
        db_session = db_session or super().get_db().session
        
        query = select(Question).where(Question.question_set_id.is_not(None))
        
        if question_set_id:
            query = query.where(Question.question_set_id == question_set_id)
        if exam_paper_id:
            query = query.where(Question.exam_paper_id == exam_paper_id)
            
        query = query.offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        return result.unique().scalars().all()

    async def get_sub_questions(
        self,
        *,
        parent_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
        db_session: AsyncSession | None = None
    ) -> list[Question]:
        """Get all sub-questions with optional parent filtering"""
        db_session = db_session or super().get_db().session
        
        query = select(Question).where(Question.parent_id.is_not(None))
        
        if parent_id:
            query = query.where(Question.parent_id == parent_id)
            
        query = query.offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        return result.unique().scalars().all()

    async def get_questions_by_type(
        self,
        *,
        question_type: str = "all",  # "main", "sub", "all"
        question_set_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        exam_paper_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 100,
        db_session: AsyncSession | None = None
    ) -> list[Question]:
        """
        Flexible method to get questions by type with various filters
        """
        db_session = db_session or super().get_db().session
        
        query = select(Question)
        
        # Apply type filtering
        if question_type == "main":
            query = query.where(Question.question_set_id.is_not(None))
            if question_set_id:
                query = query.where(Question.question_set_id == question_set_id)
            if exam_paper_id:
                query = query.where(Question.exam_paper_id == exam_paper_id)
        elif question_type == "sub":
            query = query.where(Question.parent_id.is_not(None))
            if parent_id:
                query = query.where(Question.parent_id == parent_id)
        # For "all", no additional filtering needed
        
        query = query.offset(skip).limit(limit)
        
        result = await db_session.execute(query)
        return result.unique().scalars().all()

    async def get_question_with_children(
        self,
        *,
        question_id: UUID,
        db_session: AsyncSession | None = None
    ) -> Optional[Question]:
        """Get a question with all its sub-questions loaded"""
        db_session = db_session or super().get_db().session
        
        from sqlalchemy.orm import selectinload
        
        query = (
            select(Question)
            .where(Question.id == question_id)
            .options(
                selectinload(Question.children).selectinload(Question.answers),
                selectinload(Question.answers),
                selectinload(Question.question_set),
                selectinload(Question.exam_paper),
                selectinload(Question.parent),
                selectinload(Question.created_by),
            )
        )
        
        result = await db_session.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_questions_by_slug(
        self, 
        *, 
        slug: str, 
        question_type: str = "all",
        db_session: AsyncSession | None = None
    ) -> list[Question]:
        """Search questions by slug with type filtering"""
        db_session = db_session or super().get_db().session
        
        query = select(Question).where(col(Question.slug).ilike(f"%{slug}%"))
        
        if question_type == "main":
            query = query.where(Question.question_set_id.is_not(None))
        elif question_type == "sub":
            query = query.where(Question.parent_id.is_not(None))
            
        result = await db_session.execute(query)
        return result.unique().scalars().all()

    async def count_questions_by_type(
        self,
        *,
        question_type: str = "all",
        question_set_id: Optional[UUID] = None,
        parent_id: Optional[UUID] = None,
        db_session: AsyncSession | None = None
    ) -> int:
        """Count questions by type with optional filtering"""
        db_session = db_session or super().get_db().session
        
        query = select(func.count(Question.id))
        
        if question_type == "main":
            query = query.where(Question.question_set_id.is_not(None))
            if question_set_id:
                query = query.where(Question.question_set_id == question_set_id)
        elif question_type == "sub":
            query = query.where(Question.parent_id.is_not(None))
            if parent_id:
                query = query.where(Question.parent_id == parent_id)
                
        result = await db_session.execute(query)
        return result.scalar_one()

    async def bulk_create_sub_questions(
        self,
        *,
        parent_id: UUID,
        sub_questions: list[SubQuestionCreate],
        created_by_id: UUID,
        db_session: AsyncSession | None = None
    ) -> list[Question]:
        """Bulk create sub-questions for a main question"""
        db_session = db_session or super().get_db().session
        
        # Validate parent question
        parent_question = await self.get(id=parent_id, db_session=db_session)
        if not parent_question:
            raise HTTPException(
                status_code=404,
                detail=f"Parent question with id {parent_id} not found"
            )
        
        if not parent_question.is_main_question:
            raise HTTPException(
                status_code=400,
                detail="Parent question must be a main question"
            )
        
        created_questions = []
        for sub_question_data in sub_questions:
            # Ensure parent_id is set correctly
            sub_question_data.parent_id = parent_id
            created_question = await self.create(
                obj_in=sub_question_data,
                created_by_id=created_by_id,
                db_session=db_session
            )
            created_questions.append(created_question)
        
        return created_questions

    async def delete_question_cascade(
        self,
        *,
        question_id: UUID,
        db_session: AsyncSession | None = None
    ) -> Question:
        """
        Delete a question and handle cascading for main questions
        (sub-questions will be deleted automatically due to cascade relationship)
        """
        db_session = db_session or super().get_db().session
        
        question = await self.get(id=question_id, db_session=db_session)
        if not question:
            raise HTTPException(
                status_code=404,
                detail=f"Question with id {question_id} not found"
            )
        
        # If it's a main question, warn about cascade deletion
        if question.is_main_question:
            sub_question_count = await self.count_questions_by_type(
                question_type="sub",
                parent_id=question_id,
                db_session=db_session
            )
            if sub_question_count > 0:
                # Log or handle cascade deletion warning
                pass  # Sub-questions will be deleted automatically
        
        return await self.remove(id=question_id, db_session=db_session)

    # Private validation methods
    async def _validate_main_question_creation(
        self, 
        obj_in: MainQuestionCreate, 
        db_session: AsyncSession
    ) -> None:
        """Validate main question creation data"""
        # Check if question_set exists
        from app.crud.question_set_crud import question_set
        if not await question_set.get(id=obj_in.question_set_id, db_session=db_session):
            raise HTTPException(
                status_code=404,
                detail=f"Question set with id {obj_in.question_set_id} not found"
            )
        
        # Check if exam_paper exists
        from app.crud.exam_paper_crud import exam_paper
        if not await exam_paper.get(id=obj_in.exam_paper_id, db_session=db_session):
            raise HTTPException(
                status_code=404,
                detail=f"Exam paper with id {obj_in.exam_paper_id} not found"
            )

    async def _validate_sub_question_creation(
        self, 
        obj_in: SubQuestionCreate, 
        db_session: AsyncSession
    ) -> None:
        """Validate sub-question creation data"""
        parent_question = await self.get(id=obj_in.parent_id, db_session=db_session)
        if not parent_question:
            raise HTTPException(
                status_code=404,
                detail=f"Parent question with id {obj_in.parent_id} not found"
            )
        
        if not parent_question.is_main_question:
            raise HTTPException(
                status_code=400,
                detail="Parent question must be a main question"
            )

    async def _validate_main_question_update(
        self, 
        obj_current: Question, 
        obj_new: MainQuestionUpdate, 
        db_session: AsyncSession
    ) -> None:
        """Validate main question update data"""
        # Only validate if the fields are being changed
        if obj_new.question_set_id and obj_new.question_set_id != obj_current.question_set_id:
            from app.crud.question_set_crud import question_set
            if not await question_set.get(id=obj_new.question_set_id, db_session=db_session):
                raise HTTPException(
                    status_code=404,
                    detail=f"Question set with id {obj_new.question_set_id} not found"
                )
        
        if obj_new.exam_paper_id and obj_new.exam_paper_id != obj_current.exam_paper_id:
            from app.crud.exam_paper_crud import exam_paper
            if not await exam_paper.get(id=obj_new.exam_paper_id, db_session=db_session):
                raise HTTPException(
                    status_code=404,
                    detail=f"Exam paper with id {obj_new.exam_paper_id} not found"
                )

    async def _validate_sub_question_update(
        self, 
        obj_current: Question, 
        obj_new: SubQuestionUpdate, 
        db_session: AsyncSession
    ) -> None:
        """Validate sub-question update data"""
        if obj_new.parent_id and obj_new.parent_id != obj_current.parent_id:
            parent_question = await self.get(id=obj_new.parent_id, db_session=db_session)
            if not parent_question:
                raise HTTPException(
                    status_code=404,
                    detail=f"Parent question with id {obj_new.parent_id} not found"
                )
            
            if not parent_question.is_main_question:
                raise HTTPException(
                    status_code=400,
                    detail="Parent question must be a main question"
                )

    def _get_question_type(self, question: Question) -> str:
        """Helper method to get question type as string"""
        if question.is_main_question:
            return "main"
        elif question.is_sub_question:
            return "sub"
        else:
            return "unknown"


# Create the unified CRUD instance
question = CRUDQuestion(Question)
