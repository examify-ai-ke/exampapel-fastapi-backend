from typing import Any
from app.schemas.course_schema import CourseCreate, CourseUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase

from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
# from app.utils.slugify_string import generate_slug
from app.models.course_model import Course
from app.models.programme_model import Programme
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDCourse(CRUDBase[Course, CourseCreate, CourseUpdate]):

    async def create(
        self, *, obj_in: CourseCreate, created_by_id: str = None, db_session: AsyncSession | None = None
    ) -> Course:
        db_session = db_session or super().get_db().session
        obj_in_data = obj_in.model_dump()
        if obj_in_data.get("name"):
            obj_in_data["name"] = obj_in_data["name"].title()
        db_obj = self.model(**obj_in_data)
        if created_by_id:
            db_obj.created_by_id = created_by_id
        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj

    async def update(
        self, *, obj_new: CourseUpdate, obj_current: Course, db_session: AsyncSession | None = None
    ) -> Course:
        db_session = db_session or super().get_db().session
        obj_data = obj_new.model_dump(exclude_unset=True)
        if obj_data.get("name"):
            obj_data["name"] = obj_data["name"].title()
        for key, value in obj_data.items():
            setattr(obj_current, key, value)
        db_session.add(obj_current)
        await db_session.commit()
        await db_session.refresh(obj_current)
        return obj_current

    async def get_course_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Course:
        db_session = db_session or super().get_db().session
        course = await db_session.execute(
            select(Course).where(col(Course.slug).ilike(f"%{slug}%"))
        )
        return course.unique().scalars().all()

    async def get_count_of_courses(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Course)
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

    async def update_course_image(
        self,
        *,
        course: Course,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Course:
        db_session = super().get_db().session
        course.image = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(course)
        await db_session.commit()
        await db_session.refresh(course)
        return course

    async def check_existing_association_with_programme(
        self,
        *,
        course: Course,
        programme: Programme,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session

        query = select(Course).where(
            Course.id == course.id,
            Course.programme_id == programme.id,
        )

        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record

course = CRUDCourse(Course)
