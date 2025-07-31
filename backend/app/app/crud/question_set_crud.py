from typing import Any
from app.schemas.question_schema import QuestionSetCreate, QuestionSetUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase

from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
# from app.utils.slugify_string import generate_slug

from app.models.question_model import QuestionSet
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDQuestionSet(CRUDBase[QuestionSet, QuestionSetCreate, QuestionSetUpdate]):

    async def get_question_set_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> QuestionSet:
        db_session = db_session or super().get_db().session
        q_set = await db_session.execute(
            select(QuestionSet).where(col(QuestionSet.slug).ilike(f"%{slug}%"))
        )
        return q_set.unique().scalars().all()

    # async def get_count_of_courses(
    #     self,
    #     *,
    #     # start_time: datetime,
    #     # end_time: datetime,
    #     db_session: AsyncSession | None = None,
    # ) -> int:
    #     db_session = db_session or super().get_db().session
    #     subquery = (
    #         select(Course)
    #         # .where(
    #         #     and_(
    #         #         Institution.created_at > start_time,
    #         #         Institution.created_at < end_time,
    #         #     )
    #         # )
    #         .subquery()
    #     )
    #     query = select(func.count()).select_from(subquery)
    #     count = await db_session.execute(query)
    #     value = count.scalar_one_or_none()
    #     return value




question_set= CRUDQuestionSet(QuestionSet)
