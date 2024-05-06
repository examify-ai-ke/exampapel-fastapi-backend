from typing import Any
from app.schemas.institution_schema import InstitutionCreate, InstitutionUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.institution_model import Institution, InstitutionFacultyLink
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from app.models.faculty_model import Faculty
from fastapi import HTTPException
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDInstitution(CRUDBase[Institution, InstitutionCreate, InstitutionUpdate]):

    async def get_institution_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Institution:
        db_session = db_session or super().get_db().session
        institution = await db_session.execute(
            select(Institution).where(col(Institution.slug).ilike(f"%{slug}%"))
        )
        return institution.scalars().all()

    async def get_count_of_institutions(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(Institution)
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

    async def update_institution_logo(
        self,
        *,
        institution: Institution,
        media: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Institution:
        db_session = super().get_db().session
        institution.logo = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(institution)
        await db_session.commit()
        await db_session.refresh(institution)
        return institution

    async def check_existing_association(
        self,
        *,
        institution: Institution,
        faculty: Faculty,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session
        # Check if the relationship already exists in the join table
        query = select(InstitutionFacultyLink).where(
            InstitutionFacultyLink.institution_id == institution.id,
            InstitutionFacultyLink.faculty_id == faculty.id,
        )
        existing_association = (await db_session.execute(query)).scalar_one()
        # print(existing_association.scalar_one())
        if existing_association is not None:
            return existing_association
        else:
            return None


institution = CRUDInstitution(Institution)
