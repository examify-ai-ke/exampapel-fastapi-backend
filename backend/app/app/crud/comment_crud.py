# from app.schemas.campus_schema import CampusCreate, CampusUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.comment_model import Comment
from app.schemas.comment_schema import CommentCreate, CommentUpdate, CommentReplyRead
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession
from uuid import UUID
from typing import List


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):

    # async def get_campus_by_slug(
    #     self, *, slug: str, db_session: AsyncSession | None = None
    # ) -> Comment:
    #     db_session = db_session or super().get_db().session
    #     campus = await db_session.execute(
    #         select(Comment).where(col(Comment.slug).ilike(f"%{slug}%"))
    #     )
    #     return campus.unique().scalars().all()

    async def get_count_of_comments(
        self,
        *,
        answer_id: UUID | None = None,
        db_session: AsyncSession | None = None,
    ) -> int:
        """
        Get count of comments, optionally filtered by answer_id
        
        If answer_id is provided, returns the count of comments for that specific answer
        Otherwise, returns the total count of all comments
        """
        db_session = db_session or super().get_db().session
        
        if answer_id:
            # Count comments for a specific answer
            query = select(func.count()).select_from(Comment).where(Comment.answer_id == answer_id)
        else:
            # Count all comments
            subquery = select(Comment).subquery()
            query = select(func.count()).select_from(subquery)
        
        count = await db_session.execute(query)
        value = count.scalar_one_or_none()
        return value

    async def get_comments_by_answer(
        self,
        *,
        answer_id: UUID,
        skip: int = 0,
        limit: int = 100,
        db_session: AsyncSession | None = None,
    ) -> List[Comment]:
        """Get comments for a specific answer"""
        db_session = db_session or super().get_db().session
        query = select(Comment).where(
            and_(
                Comment.answer_id == answer_id,
                Comment.parent_id == None  # Only get top-level comments
            )
        ).offset(skip).limit(limit)
        result = await db_session.execute(query)
        return result.scalars().all()

    async def like_comment(
        self,
        *,
        comment: Comment,
        db_session: AsyncSession | None = None,
    ) -> Comment:
        """Increase the like count of a comment"""
        db_session = db_session or super().get_db().session
        comment.likes += 1
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)
        return comment

    async def dislike_comment(
        self,
        *,
        comment: Comment,
        db_session: AsyncSession | None = None,
    ) -> Comment:
        """Increase the dislike count of a comment"""
        db_session = db_session or super().get_db().session
        comment.dislikes += 1
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)
        return comment



comment = CRUDComment(Comment)
