from app.schemas.programme_schema import ProgrammeCreate, ProgrammeUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.programme_model import Programme
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDProgramme(CRUDBase[Programme, ProgrammeCreate, ProgrammeUpdate]):

    async def get_programme_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Programme:
        db_session = db_session or super().get_db().session
        programme = await db_session.execute(
            select(Programme).where(col(Programme.slug).ilike(f"%{slug}%"))
        )
        return programme.unique().scalars().all()

    async def get_count_of_programmes(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Programme)
            # .where(
            #     and_(
            #         Institution.created_at > start_time,
            #         Institution.created_at < end_time,
            #     )
            # )
            .subquery()
        )
        query = select(func.count()).select_from(subquery)
        count = await db_session.execute(query)
        value = count.scalar_one_or_none()
        return value

    async def update_programme_image(
        self,
        *,
        programme: Programme,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Programme:
        db_session = super().get_db().session
        programme.image = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(programme)
        await db_session.commit()
        await db_session.refresh(programme)
        return programme


programme = CRUDProgramme(Programme)
