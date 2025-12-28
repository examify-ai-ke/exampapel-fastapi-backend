from typing import Any
from app.schemas.exam_paper_schema import ExamPaperCreate, ExamPaperUpdate
from datetime import datetime
from app.crud.base_crud import CRUDBase
from app.models.exam_paper_model import ExamPaper, ExamInstruction, ExamPaperQuestionLink, ModuleExamsLink, InstructionExamsLink
from app.schemas.media_schema import IMediaCreate
from app.models.image_media_model import ImageMedia
from app.models.media_model import Media
from app.models.faculty_model import Faculty
from app.models.module_model import   Module
from fastapi import HTTPException
from app.models.module_model import Module
from app.models.question_model import QuestionSet
from sqlmodel import select, func, and_, col
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.exam_paper_model import  ExamTitle
from app.models.course_model import Course
from app.models.exam_paper_model import  ExamDescription
from app.models.institution_model import Institution
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID

class CRUDExamPaper(CRUDBase[ExamPaper, ExamPaperCreate, ExamPaperUpdate]):

    async def get_exam_paper_by_slug(
        self, *, slug: str, db_session: AsyncSession | None = None
    ) -> ExamPaper:
        db_session = db_session or super().get_db().session
        exampaper = await db_session.execute(
            select(ExamPaper).where(col(ExamPaper.slug).ilike(f"%{slug}%"))
        )
        return exampaper.unique().scalars().first()

    async def get_all_exam_properties(self, *, db_session: AsyncSession | None = None) -> dict:
        """
        Fetch all properties related to exams from the database.
        """
        # Track if we need to close the session
        should_close_session = db_session is None

        try:
            # Get database session if not provided
            db_session = db_session or super().get_db().session

            # Define a helper function to fetch items
            async def fetch_items(model_class):
                result = await db_session.execute(select(model_class.id, model_class.name))
                return [{"id": row[0], "name": row[1]} for row in result.all()]

            # Execute all queries first, BEFORE trying to close the session
            result_dict = {
                "instructions": await fetch_items(ExamInstruction),
                "modules": await fetch_items(Module),
                "titles": await fetch_items(ExamTitle),
                "descriptions": await fetch_items(ExamDescription),
                "courses": await fetch_items(Course),
                "institutions": await fetch_items(Institution)
            }

            # We need to ensure all database operations are complete before returning
            await db_session.commit()  # If you're doing read-only operations, this is optional
            # print(result_dict)
            return result_dict

        finally:
            # Only try to close if we created the session AND all operations are done
            if should_close_session and db_session:
                try:
                    await db_session.close()
                except Exception as e:
                    # Log but don't re-raise to avoid masking the original error
                    print(f"Error closing session: {e}")

    async def get_count_of_exampapers(
        self,
        *,
        # start_time: datetime,
        # end_time: datetime,
        db_session: AsyncSession | None = None,
    ) -> int:
        db_session = db_session or super().get_db().session
        subquery = (
            select(ExamPaper)
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

    async def check_existing_association_with_module(
        self,
        *,
        exampaper: ExamPaper,
        module: Module,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session
        # Check if the relationship already exists in the join table
        query = select(ModuleExamsLink).where(
            ModuleExamsLink.exam_id == exampaper.id,
            ModuleExamsLink.module_id == module.id,
        )
        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record

    async def update_examPaper(
        self,
        *, 
        exam_paper_id: UUID,       
        obj_new: ExamPaperUpdate | dict[str, Any],
        db_session: AsyncSession | None = None,
    ) -> ExamPaper:
        try:          
            db_session =super().get_db().session
            # Retrieve the exam paper
            result = await db_session.execute(
                select(ExamPaper).where(ExamPaper.id == exam_paper_id)
            )
            # Then get the scalar from the Result
            exam_paper = result.unique().scalar_one_or_none()

            if not exam_paper:
                raise ValueError(f"No ExamPaper found with ID {exam_paper_id}")

            if isinstance(obj_new, dict):
                update_dict = obj_new
            else:
                update_dict = obj_new.model_dump(exclude_unset=True)

            # Handle nested title update
            if "title" in update_dict and update_dict["title"]:
                title_data = update_dict.pop("title")
                if title_data.get("id"):
                    # Update existing title
                    title_result = await db_session.execute(
                        select(ExamTitle).where(ExamTitle.id == title_data["id"])
                    )
                    title = title_result.scalar_one_or_none()
                    if title:
                        for key, value in title_data.items():
                            if key != "id" and value is not None:
                                setattr(title, key, value)
                        db_session.add(title)

            # Handle nested description update
            if "description" in update_dict and update_dict["description"]:
                desc_data = update_dict.pop("description")
                if desc_data.get("id"):
                    # Update existing description
                    desc_result = await db_session.execute(
                        select(ExamDescription).where(ExamDescription.id == desc_data["id"])
                    )
                    description = desc_result.scalar_one_or_none()
                    if description:
                        for key, value in desc_data.items():
                            if key != "id" and value is not None:
                                setattr(description, key, value)
                        db_session.add(description)

            # Handle nested instructions update
            if "instructions" in update_dict and update_dict["instructions"]:
                instructions_data = update_dict.pop("instructions")
                for inst_data in instructions_data:
                    if inst_data.get("id"):
                        # Update existing instruction
                        inst_result = await db_session.execute(
                            select(ExamInstruction).where(ExamInstruction.id == inst_data["id"])
                        )
                        instruction = inst_result.scalar_one_or_none()
                        if instruction:
                            for key, value in inst_data.items():
                                if key != "id" and value is not None:
                                    setattr(instruction, key, value)
                            db_session.add(instruction)

            # Handle many-to-many relationships separately
            if "instruction_ids" in update_dict:
                instruction_ids = update_dict.pop("instruction_ids")
                # Clear existing instructions
                exam_paper.instructions.clear()

                # Fetch and add new instructions
                if instruction_ids:
                    stmt = select(ExamInstruction).filter(ExamInstruction.id.in_(instruction_ids))
                    results = await db_session.execute(stmt)
                    instructions = results.unique().scalars().all()
                    if len(instructions) != len(instruction_ids):
                        raise ValueError("Some instruction IDs are invalid")
                    exam_paper.instructions.extend(instructions)

            if "module_ids" in update_dict:
                module_ids = update_dict.pop("module_ids")
                # Clear existing modules
                exam_paper.modules.clear()

                # Fetch and add new modules
                if module_ids:
                    mdl_stmt = select(Module).filter(Module.id.in_(module_ids))
                    results = await db_session.execute(mdl_stmt)
                    modules = results.unique().scalars().all()
                    if len(modules) != len(module_ids):
                        raise ValueError("Some Exam Module IDs are invalid")
                    exam_paper.modules.extend(modules)
            # Update other attributes
            for key, value in update_dict.items():
                setattr(exam_paper, key, value)

            # Commit the changes
            await db_session.commit()
            
            # Refresh the exam paper to get the updated state
            await db_session.refresh(exam_paper)
            return exam_paper

        except SQLAlchemyError as e:
            # Rollback in case of any database errors
            db_session.rollback()
            raise e

    async def check_existing_association_with_instruction(
        self,
        *,
        exampaper: ExamPaper,
        instruction: ExamInstruction,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session
        # Check if the relationship already exists in the join table
        query = select(ModuleExamsLink).where(
            InstructionExamsLink.exam_id == exampaper.id,
            InstructionExamsLink.instruction_id == instruction.id,
        )

        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record

    async def check_existing_association_with_question_set(
        self,
        *,
        exampaper: ExamPaper,
        question_set: QuestionSet,
        db_session: AsyncSession | None = None,
    ) -> Any:
        db_session = super().get_db().session
        # Check if the relationship already exists in the join table
        query = select(ExamPaperQuestionLink).where(
            ExamPaperQuestionLink.exam_id == exampaper.id,
            ExamPaperQuestionLink.question_set_id == question_set.id,
        )

        result = await db_session.execute(query)
        # Retrieve the first result or None if no result
        existing_association = result.scalar_one_or_none()

        if existing_association is None:
            return None  # Handle the case where no record is found
        else:
            return existing_association  # Return the existing record
    async def create_question_set_for_exam_paper(self,
        *,
        exam_paper_id: UUID,
        question_set_id: UUID,
        db_session: AsyncSession | None = None
        ):
        db_session = super().get_db().session

        # Create link
        link = ExamPaperQuestionLink(
            exam_id=exam_paper_id, question_set_id=question_set_id
        )
        db_session.add(link)
        await db_session.commit()
        return {"message": f"Successfully linked question set wiht exam: {exam_paper_id}"}

    async def update_exam_paper_slug(
        self,
        *,
        exam_paper: ExamPaper,
        db_session: AsyncSession | None = None,
    ) -> ExamPaper:
        """Update exam paper slug after relationships are loaded"""
        from app.utils.slugify_string import generate_slug
        
        db_session = db_session or super().get_db().session
        
        # Build slug from loaded relationships
        year = exam_paper.year_of_exam or "unknown"
        exam_description = exam_paper.description.name if exam_paper.description else "no-desc"
        institution_name = exam_paper.institution.name if exam_paper.institution else "no-inst"
        course_name = exam_paper.course.name if exam_paper.course else "no-course"
        title_name = exam_paper.title.name if exam_paper.title else "no-title"
        exam_date = exam_paper.exam_date.strftime("%Y-%m-%d") if exam_paper.exam_date else "no-date"
        exam_module = exam_paper.modules[0].name if exam_paper.modules else "-"
        hash_suffix = exam_paper.hash_code[:12] if exam_paper.hash_code else "temp"
        
        slug_string = f"{year}-{exam_description}-{institution_name}-{course_name}-{exam_module}-{hash_suffix}"
        exam_paper.slug = generate_slug(slug_string)
        
        db_session.add(exam_paper)
        await db_session.commit()
        await db_session.refresh(exam_paper)
        
        return exam_paper


exam_paper = CRUDExamPaper(ExamPaper)


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
