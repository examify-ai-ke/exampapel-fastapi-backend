from typing import Any
from app.schemas.exam_paper_schema import InstructionCreate, InstructionUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.exam_paper_model import  ExamInstruction,InstructionExamsLink
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media


from fastapi import HTTPException
from app.models.module_model import Module
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession


class CRUDInstruction(CRUDBase[ExamInstruction, InstructionCreate, InstructionUpdate]):

    async def get_instructions_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> ExamInstruction:
        db_session = db_session or super().get_db().session
        instruction = await db_session.execute(
            select(ExamInstruction).where(col(ExamInstruction.slug).ilike(f"%{slug}%"))
        )
        return instruction.unique().scalars().all()

    # async def get_count_of_exampapers(
    #     self,
    #     *,
    #     # start_time: datetime,
    #     # end_time: datetime,
    #     db_session: AsyncSession | None = None,
    # ) -> int:
    #     db_session = db_session or super().get_db().session
    #     subquery = (
    #         select(ExamPaper)
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
    #     value = count.unique().scalar_one_or_none()
    #     return value

    # async def update_institution_logo(
    #     self,
    #     *,
    #     institution: Institution,
    #     media: IMediaCreate,
    #     heigth: int,
    #     width: int,
    #     file_format: str,
    # ) -> Institution:
    #     db_session = super().get_db().session
    #     institution.logo = ImageMedia(
    #         media=Media.model_validate(media),
    #         height=heigth,
    #         width=width,
    #         file_format=file_format,
    #     )
    #     db_session.add(institution)
    #     await db_session.commit()
    #     await db_session.refresh(institution)
    #     return institution

    # async def check_existing_association_with_module(
    #     self,
    #     *,
    #     exampaper: ExamPaper,
    #     module: Module,
    #     db_session: AsyncSession | None = None,
    # ) -> Any:
    #     db_session = super().get_db().session
    #     # Check if the relationship already exists in the join table
    #     query = select(ModuleExamsLink).where(
    #         ModuleExamsLink.exam_id == exampaper.id,
    #         ModuleExamsLink.module_id == module.id,
    #     )

    #     result = await db_session.execute(query)
    #     # Retrieve the first result or None if no result
    #     existing_association = result.scalar_one_or_none()

    #     if existing_association is None:
    #         return None  # Handle the case where no record is found
    #     else:
    #         return existing_association  # Return the existing record

    # async def check_existing_association_with_instruction(
    #     self,
    #     *,
    #     exampaper: ExamPaper,
    #     instruction: ExamInstruction,
    #     db_session: AsyncSession | None = None,
    # ) -> Any:
    #     db_session = super().get_db().session
    #     # Check if the relationship already exists in the join table
    #     query = select(ModuleExamsLink).where(
    #         InstructionExamsLink.exam_id == exampaper.id,
    #         InstructionExamsLink.instruction_id == instruction.id,
    #     )

    #     result = await db_session.execute(query)
    #     # Retrieve the first result or None if no result
    #     existing_association = result.scalar_one_or_none()

    #     if existing_association is None:
    #         return None  # Handle the case where no record is found
    #     else:
    #         return existing_association  # Return the existing record


instruction = CRUDInstruction(ExamInstruction)


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
