from typing import Any
from app.schemas.faculty_schema import FacultyCreate, FacultyUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.faculty_model import Faculty
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from app.models.department_model import Department
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDFaculty(CRUDBase[Faculty, FacultyCreate, FacultyUpdate]):

    async def get_faculty_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Faculty:
        db_session = db_session or super().get_db().session
        faculty = await db_session.execute(
            select(Faculty).where(col(Faculty.slug).ilike(f"%{slug}%"))
        )
        return faculty.unique().scalars().all()

    async def get_count_of_faculties(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Faculty)
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

    async def update_faculty_image(
        self,
        *,
        faculty: Faculty,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Faculty:
        db_session = super().get_db().session
        faculty.image= ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(faculty)
        await db_session.commit()
        await db_session.refresh(faculty)
        return faculty

    async def check_existing_faculty_department_association(
        self,
        *,
        department: Department,
        faculty:Faculty,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session
        # Check if the relationship already exists in the join table
        query = select(Department).where(
            Department.faculty_id == faculty.id, Department.id==department.id
        )

        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record


faculty = CRUDFaculty(Faculty)
