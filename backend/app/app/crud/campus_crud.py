from app.schemas.campus_schema import CampusCreate, CampusUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.campus_model import Campus
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDCampus(CRUDBase[Campus, CampusCreate, CampusUpdate]):

    async def get_campus_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Campus:
        db_session = db_session or super().get_db().session
        campus = await db_session.execute(
            select(Campus).where(col(Campus.slug).ilike(f"%{slug}%"))
        )
        return campus.unique().scalars().all()

    async def get_count_of_campus(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Campus)
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

    async def update_campus_image(
        self,
        *,
        campus: Campus,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Campus:
        db_session = super().get_db().session
        campus.image = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(campus)
        await db_session.commit()
        await db_session.refresh(campus)
        return campus


campus = CRUDCampus(Campus)
