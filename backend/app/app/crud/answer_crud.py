from typing import Any, List
from app.schemas.answer_schema import AnswerCreate, AnswerUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.answer_model import Answer
from app.models.question_model import Question
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload


class CRUDAnswer(CRUDBase[Answer, AnswerCreate, AnswerUpdate]):
    
    async def get_answers_by_question(
        self, *, question_id: UUID, db_session: AsyncSession | None = None
    ) -> List[Answer]:
        """Get all answers for a specific question"""
        db_session = db_session or super().get_db().session
        query = (
            select(Answer)
            .where(Answer.question_id == question_id)
            .options(
                selectinload(Answer.created_by),
                selectinload(Answer.question),
                selectinload(Answer.parent),
                selectinload(Answer.children).selectinload(Answer.created_by),
                selectinload(Answer.children).selectinload(Answer.question),
            )
        )
        result = await db_session.execute(query)
        answers = result.unique().scalars().all()
        
        # Ensure all relationships are loaded
        for answer in answers:
            _ = answer.created_by
            _ = answer.question
            _ = answer.parent
            _ = answer.children
            for child in answer.children:
                _ = child.created_by
                _ = child.question
        
        return answers
    
    async def get_top_level_answers_by_question(
        self, *, question_id: UUID, db_session: AsyncSession | None = None
    ) -> List[Answer]:
        """Get only top-level answers (no parent) for a specific question"""
        db_session = db_session or super().get_db().session
        query = (
            select(Answer)
            .where(
                and_(
                    Answer.question_id == question_id,
                    Answer.parent_id.is_(None)
                )
            )
            .options(
                selectinload(Answer.created_by),
                selectinload(Answer.question),
                selectinload(Answer.children).selectinload(Answer.created_by),
                selectinload(Answer.children).selectinload(Answer.question),
            )
        )
        result = await db_session.execute(query)
        answers = result.unique().scalars().all()
        
        # Ensure all relationships are loaded
        for answer in answers:
            _ = answer.created_by
            _ = answer.question
            _ = answer.children
            for child in answer.children:
                _ = child.created_by
                _ = child.question
        
        return answers
    
    async def get_answer_with_children(
        self, *, answer_id: UUID, db_session: AsyncSession | None = None
    ) -> Answer | None:
        """Get an answer with all its children (nested replies)"""
        db_session = db_session or super().get_db().session
        query = (
            select(Answer)
            .where(Answer.id == answer_id)
            .options(
                selectinload(Answer.created_by),
                selectinload(Answer.question),
                selectinload(Answer.children).selectinload(Answer.created_by),
                selectinload(Answer.children).selectinload(Answer.question),
                selectinload(Answer.children).selectinload(Answer.children).selectinload(Answer.created_by),
                selectinload(Answer.children).selectinload(Answer.children).selectinload(Answer.question),
            )
        )
        result = await db_session.execute(query)
        answer = result.unique().scalar_one_or_none()
        
        if answer:
            # Ensure all relationships are loaded
            _ = answer.created_by
            _ = answer.question
            _ = answer.children
            for child in answer.children:
                _ = child.created_by
                _ = child.question
                _ = child.children
                for grandchild in child.children:
                    _ = grandchild.created_by
                    _ = grandchild.question
        
        return answer
    
    async def create_answer_for_question(
        self, 
        *, 
        answer_data: AnswerCreate, 
        created_by_id: UUID,
        db_session: AsyncSession | None = None
    ) -> Answer:
        """Create a new answer for a question"""
        db_session = db_session or super().get_db().session
        
        # Verify the question exists
        question_query = select(Question).where(Question.id == answer_data.question_id)
        question_result = await db_session.execute(question_query)
        question = question_result.scalar_one_or_none()
        
        if not question:
            raise HTTPException(
                status_code=404, 
                detail=f"Question with id {answer_data.question_id} not found"
            )
        
        # Create the answer
        answer = Answer(
            text=answer_data.text.model_dump() if answer_data.text else {},
            question_id=answer_data.question_id,
            created_by_id=created_by_id
        )
        
        db_session.add(answer)
        await db_session.commit()
        await db_session.refresh(answer)
        
        return answer
    
    async def create_reply_to_answer(
        self,
        *,
        parent_answer_id: UUID,
        answer_data: AnswerCreate,
        created_by_id: UUID,
        db_session: AsyncSession | None = None
    ) -> Answer:
        """Create a reply to an existing answer"""
        db_session = db_session or super().get_db().session
        
        # Verify the parent answer exists
        parent_query = select(Answer).where(Answer.id == parent_answer_id)
        parent_result = await db_session.execute(parent_query)
        parent_answer = parent_result.scalar_one_or_none()
        
        if not parent_answer:
            raise HTTPException(
                status_code=404,
                detail=f"Parent answer with id {parent_answer_id} not found"
            )
        
        # Create the reply
        reply = Answer(
            text=answer_data.text.model_dump() if answer_data.text else {},
            question_id=answer_data.question_id,
            parent_id=parent_answer_id,
            created_by_id=created_by_id
        )
        
        db_session.add(reply)
        await db_session.commit()
        await db_session.refresh(reply)
        
        return reply
    
    async def update_answer_likes(
        self,
        *,
        answer_id: UUID,
        likes: int,
        db_session: AsyncSession | None = None
    ) -> Answer:
        """Update the likes count for an answer"""
        db_session = db_session or super().get_db().session
        
        answer = await self.get(id=answer_id, db_session=db_session)
        if not answer:
            raise HTTPException(
                status_code=404,
                detail=f"Answer with id {answer_id} not found"
            )
        
        answer.likes = likes
        db_session.add(answer)
        await db_session.commit()
        await db_session.refresh(answer)
        
        return answer
    
    async def update_answer_dislikes(
        self,
        *,
        answer_id: UUID,
        dislikes: int,
        db_session: AsyncSession | None = None
    ) -> Answer:
        """Update the dislikes count for an answer"""
        db_session = db_session or super().get_db().session
        
        answer = await self.get(id=answer_id, db_session=db_session)
        if not answer:
            raise HTTPException(
                status_code=404,
                detail=f"Answer with id {answer_id} not found"
            )
        
        answer.dislikes = dislikes
        db_session.add(answer)
        await db_session.commit()
        await db_session.refresh(answer)
        
        return answer
    
    async def mark_answer_as_reviewed(
        self,
        *,
        answer_id: UUID,
        reviewed: bool = True,
        db_session: AsyncSession | None = None
    ) -> Answer:
        """Mark an answer as reviewed or unreviewed"""
        db_session = db_session or super().get_db().session
        
        answer = await self.get(id=answer_id, db_session=db_session)
        if not answer:
            raise HTTPException(
                status_code=404,
                detail=f"Answer with id {answer_id} not found"
            )
        
        answer.reviewed = reviewed
        db_session.add(answer)
        await db_session.commit()
        await db_session.refresh(answer)
        
        return answer
    
    async def get_answers_count_by_question(
        self, *, question_id: UUID, db_session: AsyncSession | None = None
    ) -> int:
        """Get the count of answers for a specific question"""
        db_session = db_session or super().get_db().session
        query = select(func.count(Answer.id)).where(Answer.question_id == question_id)
        result = await db_session.execute(query)
        return result.scalar_one()


answer = CRUDAnswer(Answer)
