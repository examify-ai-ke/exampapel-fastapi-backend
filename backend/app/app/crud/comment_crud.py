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
        # Eager load user and image, and reples with their user and image
        from sqlalchemy.orm import selectinload
        from app.models.user_model import User
        
        query = select(Comment).where(
            and_(
                Comment.answer_id == answer_id,
                Comment.parent_id == None  # Only get top-level comments
            )
        ).options(
            selectinload(Comment.created_by).selectinload(User.image),
            selectinload(Comment.replies).options(
                selectinload(Comment.created_by).selectinload(User.image)
            )
        )
        
        if order == IOrderEnum.ascendent:
            query = query.order_by(columns[order_by].asc())
        else:
            # Default to descending
            query = query.order_by(columns[order_by].desc())

        # Return paginated results
        return await paginate(db_session, query, params)

    async def get_replies_by_parent(
        self,
        *,
        parent_id: UUID,
        skip: int = 0,
        limit: int = 50,
        order_by: str | None = None,
        order: IOrderEnum | None = IOrderEnum.ascendent, # Default replies to oldest first usually
        db_session: AsyncSession | None = None,
    ) -> Page[Comment]:
        """
        Get paginated replies for a specific comment
        """
        db_session = db_session or super().get_db().session
        params = Params(page=skip // limit + 1, size=limit)

        columns = self.model.__table__.columns
        if order_by is None or order_by not in columns:
            order_by = "created_at"

        from sqlalchemy.orm import selectinload
        from app.models.user_model import User

        query = select(Comment).where(Comment.parent_id == parent_id)\
            .options(
                selectinload(Comment.created_by).selectinload(User.image)
            )

        if order == IOrderEnum.ascendent:
            query = query.order_by(columns[order_by].asc())
        else:
            query = query.order_by(columns[order_by].desc())

        return await paginate(db_session, query, params)


    async def toggle_comment_like(
        self,
        *,
        comment_id: UUID,
        user_id: UUID,
        db_session: AsyncSession | None = None,
    ) -> Comment:
        """Toggle like for a comment"""
        from app.models.comment_model import CommentVote
        
        db_session = db_session or super().get_db().session
        
        comment = await self.get(id=comment_id, db_session=db_session)
        if not comment:
            raise HTTPException(
                status_code=404,
                detail=f"Comment with id {comment_id} not found"
            )
        
        # Check if user has already voted
        vote_query = select(CommentVote).where(
            and_(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id
            )
        )
        vote_result = await db_session.execute(vote_query)
        existing_vote = vote_result.scalar_one_or_none()
        
        if existing_vote:
            if existing_vote.vote_type == "like":
                # Unlike - remove the vote
                await db_session.delete(existing_vote)
                comment.likes = max(0, comment.likes - 1)
            else:
                # Change from dislike to like
                existing_vote.vote_type = "like"
                comment.dislikes = max(0, comment.dislikes - 1)
                comment.likes += 1
        else:
            # New like
            new_vote = CommentVote(
                comment_id=comment_id,
                user_id=user_id,
                vote_type="like"
            )
            db_session.add(new_vote)
            comment.likes += 1
        
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)
        return comment

    async def toggle_comment_dislike(
        self,
        *,
        comment_id: UUID,
        user_id: UUID,
        db_session: AsyncSession | None = None,
    ) -> Comment:
        """Toggle dislike for a comment"""
        from app.models.comment_model import CommentVote
        
        db_session = db_session or super().get_db().session
        
        comment = await self.get(id=comment_id, db_session=db_session)
        if not comment:
            raise HTTPException(
                status_code=404,
                detail=f"Comment with id {comment_id} not found"
            )
        
        # Check if user has already voted
        vote_query = select(CommentVote).where(
            and_(
                CommentVote.comment_id == comment_id,
                CommentVote.user_id == user_id
            )
        )
        vote_result = await db_session.execute(vote_query)
        existing_vote = vote_result.scalar_one_or_none()
        
        if existing_vote:
            if existing_vote.vote_type == "dislike":
                # Undislike - remove the vote
                await db_session.delete(existing_vote)
                comment.dislikes = max(0, comment.dislikes - 1)
            else:
                # Change from like to dislike
                existing_vote.vote_type = "dislike"
                comment.likes = max(0, comment.likes - 1)
                comment.dislikes += 1
        else:
            # New dislike
            new_vote = CommentVote(
                comment_id=comment_id,
                user_id=user_id,
                vote_type="dislike"
            )
            db_session.add(new_vote)
            comment.dislikes += 1
        
        db_session.add(comment)
        await db_session.commit()
        await db_session.refresh(comment)
        return comment


comment = CRUDComment(Comment)
