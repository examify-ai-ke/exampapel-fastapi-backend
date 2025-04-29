from typing import Any
from app.schemas.institution_schema import InstitutionCreate, InstitutionUpdate
from app.schemas.address_schema import AddressCreate, AddressUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.institution_model import Institution, InstitutionFacultyLink, Address
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from app.models.faculty_model import Faculty

from app.models.campus_model import Campus
from app.models.exam_paper_model import ExamPaper
from fastapi import HTTPException
from sqlmodel import select, func, and_, col
from sqlalchemy.orm import selectinload  
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user_model import User


class CRUDInstitution(CRUDBase[Institution, InstitutionCreate, InstitutionUpdate]):

    async def get_institution_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Institution:
        db_session = db_session or super().get_db().session
        query = (
            select(Institution)
            .where(col(Institution.slug).ilike(f"%{slug}%"))
            .options(
                selectinload(Institution.faculties),
                selectinload(Institution.campuses),
                selectinload(Institution.exam_papers),
                selectinload(Institution.logo),
                selectinload(Institution.created_by),
                selectinload(Institution.address),
            )
        )
        result = await db_session.execute(query)
        return result.unique().scalars().all()

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
        value = count.unique().scalar_one_or_none()
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
        # print(media)
        institution.logo = ImageMedia(
            media=Media.model_validate(media),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(institution)
        await db_session.commit()
        await db_session.refresh(institution)
        # print("update_institution_logo")
        # print(institution)
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

        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record

    async def create(
        self, *, obj_in: InstitutionCreate, created_by_id: str = None, db_session: AsyncSession | None = None
    ) -> Institution:
        db_session = db_session or super().get_db().session

        # Extract address data if provided
        address_data = obj_in.address
        address_obj = None

        # Remove address from institution data for model creation
        obj_in_data = obj_in.model_dump(exclude={"address"})

        # Create institution
        db_obj = self.model(**obj_in_data)
        if created_by_id:
            db_obj.created_by_id = created_by_id

        # If address data is provided, create address
        if address_data:
            address_obj = Address(**address_data.model_dump())
            db_session.add(address_obj)
            await db_session.flush()  # Flush to get the address ID

            # Link address to institution
            db_obj.address = address_obj

        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj

    async def update(
        self, *, obj_new: InstitutionUpdate, obj_current: Institution, db_session: AsyncSession | None = None
    ) -> Institution:
        db_session = db_session or super().get_db().session

        # Handle address update if provided
        address_data = obj_new.address
        if address_data and address_data.model_dump(exclude_unset=True):
            # If institution has no address yet, create one
            if not obj_current.address:
                address_obj = Address(**address_data.model_dump(exclude_unset=True))
                db_session.add(address_obj)
                await db_session.flush()
                obj_current.address = address_obj
            else:
                # Update existing address
                for key, value in address_data.model_dump(exclude_unset=True).items():
                    setattr(obj_current.address, key, value)

        # Update institution fields (excluding address)
        obj_data = obj_new.model_dump(exclude={"address"}, exclude_unset=True)
        for key, value in obj_data.items():
            setattr(obj_current, key, value)

        db_session.add(obj_current)
        await db_session.commit()
        await db_session.refresh(obj_current)
        return obj_current


institution = CRUDInstitution(Institution)

