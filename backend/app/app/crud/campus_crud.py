from app.schemas.campus_schema import CampusCreate, CampusUpdate
from app.schemas.address_schema import AddressCreate, AddressUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.campus_model import Campus
from app.models.institution_model import Address
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from sqlmodel import select, func, and_, col
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDCampus(CRUDBase[Campus, CampusCreate, CampusUpdate]):

    async def get_campus_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> Campus:
        db_session = db_session or super().get_db().session
        query = (
            select(Campus)
            .where(col(Campus.slug).ilike(f"%{slug}%"))
            .options(
                selectinload(Campus.institution),
                selectinload(Campus.address),
                selectinload(Campus.created_by),
            )
        )
        result = await db_session.execute(query)
        return result.unique().scalars().all()

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
        image: IMediaCreate,
        heigth: int,
        width: int,
        file_format: str,
    ) -> Campus:
        db_session = super().get_db().session
        campus.image = ImageMedia(
            media=Media.model_validate(image),
            height=heigth,
            width=width,
            file_format=file_format,
        )
        db_session.add(campus)
        await db_session.commit()
        await db_session.refresh(campus)
        return campus
        
    async def create(
        self, *, obj_in: CampusCreate, created_by_id: str = None, db_session: AsyncSession | None = None
    ) -> Campus:
        db_session = db_session or super().get_db().session
        
        # Extract address data if provided
        address_data = obj_in.address
        address_obj = None
        
        # Remove address from campus data for model creation
        obj_in_data = obj_in.model_dump(exclude={"address"})
        
        # Create campus
        db_obj = self.model(**obj_in_data)
        if created_by_id:
            db_obj.created_by_id = created_by_id
            
        # If address data is provided, create address
        if address_data:
            address_obj = Address(**address_data.model_dump())
            db_session.add(address_obj)
            await db_session.flush()  # Flush to get the address ID
            
            # Link address to campus
            db_obj.address = address_obj
            
        db_session.add(db_obj)
        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj
        
    async def update(
        self, *, obj_new: CampusUpdate, obj_current: Campus, db_session: AsyncSession | None = None
    ) -> Campus:
        db_session = db_session or super().get_db().session
        
        # Handle address update if provided
        address_data = obj_new.address
        if address_data and address_data.model_dump(exclude_unset=True):
            # If campus has no address yet, create one
            if not obj_current.address:
                address_obj = Address(**address_data.model_dump(exclude_unset=True))
                db_session.add(address_obj)
                await db_session.flush()
                obj_current.address = address_obj
            else:
                # Update existing address
                for key, value in address_data.model_dump(exclude_unset=True).items():
                    setattr(obj_current.address, key, value)
        
        # Update campus fields (excluding address)
        obj_data = obj_new.model_dump(exclude={"address"}, exclude_unset=True)
        for key, value in obj_data.items():
            setattr(obj_current, key, value)
            
        db_session.add(obj_current)
        await db_session.commit()
        await db_session.refresh(obj_current)
        return obj_current


campus = CRUDCampus(Campus)
