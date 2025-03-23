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
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_pagination import Params, Page
from app.schemas.common_schema import IOrderEnum


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):

    async def get_count_of_comments(
        self,
        *,
        answer_id: UUID,
        db_session: AsyncSession | None = None,
    ) -> int:
        """
        Get count of comments, optionally filtered by answer_id
        
        If answer_id is provided, returns the count of comments for that specific answer
        Otherwise, returns the total count of all comments
        """
        db_session = db_session or super().get_db().session

        try:
            if answer_id:
                # Count comments for a specific answer
                query = select(func.count(Comment.id)).where(Comment.answer_id == answer_id)
                print(f"Counting comments for answer_id: {answer_id}")
            else:
                # Count all comments
                query = select(func.count(Comment.id))
                print("Counting all comments")

            count = await db_session.execute(query)
            value = count.scalar_one_or_none() or 0  # Default to 0 if None
            print(f"Count result: {value}")
            return value
        except Exception as e:
            print(f"Error counting comments: {str(e)}")
            # Log the error for debugging
            return 0

    async def get_comments_by_answer(
        self,
        *,
        answer_id: UUID,
        skip: int = 0,
        limit: int = 50,
        order_by: str | None = None,
        order: IOrderEnum | None = IOrderEnum.descendent,
        db_session: AsyncSession | None = None,
    ) -> Page[Comment]:
        """
        Get paginated comments for a specific answer with ordering
        
        Returns top-level comments (without parent) for the specified answer
        """
        db_session = db_session or super().get_db().session
        params = Params(page=skip // limit + 1, size=limit)  # Convert skip/limit to page/size

        # Get the model columns for ordering
        columns = self.model.__table__.columns

        # Default to ordering by created_at if no valid column is provided
        if order_by is None or order_by not in columns:
            order_by = "created_at"

        # Build the query with filtering and ordering
        if order == IOrderEnum.ascendent:
            query = select(Comment).where(
                and_(
                    Comment.answer_id == answer_id,
                    Comment.parent_id == None  # Only get top-level comments
                )
            ).order_by(columns[order_by].asc())
        else:
            query = select(Comment).where(
                and_(
                    Comment.answer_id == answer_id,
                    Comment.parent_id == None  # Only get top-level comments
                )
            ).order_by(columns[order_by].desc())

        # Return paginated results
        return await paginate(db_session, query, params)

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
