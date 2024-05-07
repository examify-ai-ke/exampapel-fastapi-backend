from app.schemas.department_schema import DepartmentCreate, DepartmentUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.department_model import Department
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDDepartment(CRUDBase[Department, DepartmentCreate, DepartmentUpdate]):

    async def get_department_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Department:
        db_session = db_session or super().get_db().session
        department = await db_session.execute(
            select(Department).where(col(Department.slug).ilike(f"%{slug}%"))
        )
        return department.scalars().all()

    async def get_count_of_departments(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Department)
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

    async def update_department_image(
        self,
        *,
        department: Department,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Department:
        db_session = super().get_db().session
        department.image = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(department)
        await db_session.commit()
        await db_session.refresh(department)
        return department


department = CRUDDepartment(Department)
