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


# from fastapi import FastAPI, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from app.models import Institution, Faculty, InstitutionFaculty  # Import your models
# from app.database import get_db  # Dependency for database session
# from uuid import UUID
# from typing import List

# app = FastAPI()


# # Schema for adding multiple faculties to an institution
# class AddFacultiesToInstitutionRequest(BaseModel):
#     faculty_ids: List[UUID]  # List of UUIDs representing faculties to add


# @app.post("/institutions/{institution_id}/faculties")
# async def add_faculties_to_institution(
#     institution_id: UUID,
#     request: AddFacultiesToInstitutionRequest,
#     db: AsyncSession = Depends(get_db),
# ):
#     # Ensure the institution exists
#     institution = await db.get(Institution, institution_id)
#     if not institution:
#         raise HTTPException(status_code=404, detail="Institution not found")

#     # Retrieve the faculties from the given list of faculty IDs
#     faculty_ids = request.faculty_ids
#     faculties = await db.execute(select(Faculty).where(Faculty.id.in_(faculty_ids)))
#     faculties_list = faculties.scalars().all()

#     # Check if any of the faculty IDs do not exist
#     existing_faculty_ids = {faculty.id for faculty in faculties_list}
#     missing_faculty_ids = set(faculty_ids) - existing_faculty_ids
#     if missing_faculty_ids:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Faculties with IDs {missing_faculty_ids} not found",
#         )

#     # Check for existing associations to avoid duplicates
#     existing_associations = await db.execute(
#         select(InstitutionFaculty).where(
#             InstitutionFaculty.institution_id == institution_id,
#             InstitutionFaculty.faculty_id.in_(faculty_ids),
#         )
#     )
#     existing_associations_set = {
#         assoc.faculty_id for assoc in existing_associations.scalars().all()
#     }
#     duplicate_faculty_ids = set(faculty_ids) & existing_associations_set

#     if duplicate_faculty_ids:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Faculties with IDs {duplicate_faculty_ids} are already associated with Institution '{institution_id}'",
#         )

#     # If everything is valid, add the faculties to the institution
#     for faculty in faculties_list:
#         institution.faculties.append(faculty)

#     await db.commit()

#     return {
#         "message": f"Successfully added faculties to Institution '{institution_id}'"
#     }
