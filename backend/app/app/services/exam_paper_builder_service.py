from uuid import UUID
from typing import List, Optional, Any, Dict
import enum
from sqlalchemy.future import select
from sqlalchemy import func
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.user_model import User
from app.schemas.exam_paper_builder_schema import CompleteExamPaperCreate
from app.crud import (
    institution as crud_institution,
    programme as crud_programme,
    course as crud_course,
    exam_title as crud_exam_title,
    exam_description as crud_exam_description,
    module as crud_module,
    instruction as crud_instruction,
    exam_paper as crud_exam_paper,
    question_set as crud_question_set,
    question as crud_question
)
from app.schemas.institution_schema import InstitutionCreate
from app.schemas.programme_schema import ProgrammeCreate
from app.schemas.course_schema import CourseCreate
from app.schemas.module_schema import ModuleCreate
from app.schemas.exam_paper_schema import (
    ExamPaperCreate, 
    InstructionCreate,
    ExamTitleCreate,
    ExamDescriptionCreate
)
from app.schemas.question_schema import QuestionSetCreate, MainQuestionCreate, SubQuestionCreate
from app.models.exam_paper_model import ExamPaper, ExamTitle, ExamDescription, ExamInstruction
from app.models.institution_model import Institution
from app.models.programme_model import Programme
from app.models.course_model import Course
from app.models.module_model import Module
from app.models.question_model import QuestionSet, QuestionSetTitleEnum
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class ExamPaperBuilderService:
    
    async def _get_or_create_by_name(
        self, 
        db: AsyncSession, 
        model_class: Any, 
        crud_instance: Any, 
        schema_create: Any, 
        name: Any, 
        extra_data: Dict[str, Any], 
        user_id: UUID,
        lookup_field: str = "name"
    ) -> Any:
        """Generic helper to get by name or create"""
        # specialized check for names that might need sanitization or specific queries
        # For now assume 'name' column exists and is unique-ish or we just want first match
        # 1. Check if exists
        print(f"DEBUG: Checking for {model_class.__name__} with {lookup_field}='{name}' (Type: {type(name)})")
        
        column = getattr(model_class, lookup_field)
        
        if isinstance(name, str):
            # Case-insensitive lookup for string names to match what inserter.py does
            # and to handle models that normalize casing (like ExamDescription.name)
            query = select(model_class).where(func.lower(column) == name.lower())
        else:
            query = select(model_class).where(column == name)
            
        # Add extra filters if needed (e.g. for Course if we wanted to filter by programme, but keeping it simple)
        
        result = await db.execute(query)
        instance = result.scalars().first()
        
        if instance:
            print(f"DEBUG: Found existing {model_class.__name__}: {instance.id}")
            return instance
            
        print(f"DEBUG: Not found, creating {model_class.__name__}...")
        # Create
        create_data = extra_data.copy()
        if lookup_field not in create_data:
            create_data[lookup_field] = name
            
        # Some schemas might require generic instantiation
        obj_in = schema_create(**create_data)
        return await crud_instance.create(db_session=db, obj_in=obj_in, created_by_id=user_id)

    async def create_complete_exam_paper(
        self,
        db: AsyncSession,
        data: CompleteExamPaperCreate,
        user: User
    ) -> ExamPaper:
        user_id = user.id
        prereqs = data.prerequisites
        
        # 1. Institution
        inst_data = prereqs.institution
        institution = await self._get_or_create_by_name(
            db, Institution, crud_institution, InstitutionCreate, 
            inst_data.name, 
            inst_data.model_dump(exclude={"name"}) if inst_data else {},
            user_id
        )
        
        # 2. Programme
        prog_data = prereqs.programme
        programme = None
        if prog_data:
             prog_lookup = prog_data.name
             # Handle Enum: If pydantic parsed it as Enum, get name.
             if isinstance(prog_lookup, enum.Enum):
                 prog_lookup = prog_lookup.name
             # If it's a string that matches an enum value (e.g. "Bachelors/Undergraduate"), find the name (e.g. "BACHELORS")
             elif isinstance(prog_lookup, str):
                 # Try to find the enum member by value
                 from app.models.programme_model import ProgrammeTypes
                 for member in ProgrammeTypes:
                     if member.value == prog_lookup:
                         prog_lookup = member
                         break
                 
             programme = await self._get_or_create_by_name(
                db, Programme, crud_programme, ProgrammeCreate,
                prog_lookup,
                prog_data.model_dump(), # Include name for creation
                user_id
            )
            
        # 3. Exam Title
        title_data = prereqs.exam_title
        exam_title = await self._get_or_create_by_name(
            db, ExamTitle, crud_exam_title, ExamTitleCreate,
            title_data.name,
            title_data.model_dump(exclude={"name"}) if title_data else {},
            user_id
        )
        
        # 4. Exam Description
        desc_data = prereqs.exam_description
        exam_description = await self._get_or_create_by_name(
            db, ExamDescription, crud_exam_description, ExamDescriptionCreate,
            desc_data.name,
            desc_data.model_dump(exclude={"name"}) if desc_data else {},
            user_id
        )
        
        # 5. Course
        course_data = prereqs.course
        course_extra = course_data.model_dump(exclude={"name"}) if course_data else {}
        if programme:
            course_extra["programme_id"] = programme.id
            
        # Course creation might fail if programme_id is missing but schema requires it.
        # Assuming we always have programme if course is provided, or we handle error.
        if not programme and "programme_id" not in course_extra:
             # Fallback: Try to find a default programme or error? 
             # For now let's hope it's either existing course or programme is provided
             pass

        course = await self._get_or_create_by_name(
            db, Course, crud_course, CourseCreate,
            course_data.name,
            course_extra,
            user_id
        )
        
        # 6. Modules
        module_ids = []
        for mod in prereqs.modules:
            module_obj = await self._get_or_create_by_name(
                db, Module, crud_module, ModuleCreate,
                mod.name,
                mod.model_dump(exclude={"name"}),
                user_id
            )
            module_ids.append(module_obj.id)
            
        # 7. Instructions
        instruction_ids = []
        for instr in prereqs.instructions:
             instr_obj = await self._get_or_create_by_name(
                db, ExamInstruction, crud_instruction, InstructionCreate,
                instr.name,
                {},
                user_id
            )
             instruction_ids.append(instr_obj.id)
             
        # 8. Create Exam Paper
        ep_data = data.exam_paper
        
        # Construct ExamPaperCreate schema
        # We need to map fields. 
        # Note: ExamPaperCreate requires title_id, etc.
        
        exam_paper_in = ExamPaperCreate(
            title_id=exam_title.id,
            description_id=exam_description.id,
            course_id=course.id,
            institution_id=institution.id,
            year_of_exam=ep_data.year_of_exam,
            exam_duration=ep_data.exam_duration,
            exam_date=ep_data.exam_date,
            tags=ep_data.tags,
            module_ids=module_ids,
            instruction_ids=instruction_ids
        )
        
        # Check if already exists to avoid duplicates?
        # The crud.create usually handles it or raises error.
        # But we want to be idempotent ideally. 
        # For now, let's try create, if it fails, we might need to fetch existing.
        # Implementing simple fetch-if-exists logic:
        # Check by some uniqueness (e.g. course + year + title) logic is complex.
        # Let's trust crud.create or catch error.
        
        try:
            exam_paper = await crud_exam_paper.create(db_session=db, obj_in=exam_paper_in, created_by_id=user_id)
        except Exception as e:
            # If duplicate, we might want to fetch it.
            # But the 'hash_code' is unique.
            # It's hard to reconstruct hash_code exactly without logic.
            # Let's assume for this builder we want new ones or fail.
            # Or better, search by identifying fields?
            # Let's log and re-raise for now.
            logger.error(f"Failed to create exam paper: {e}")
            raise HTTPException(status_code=400, detail=f"Could not create exam paper: {str(e)}")

        # 9. Questions
        for qs_data in data.questions.question_sets:
            # Create Question Set
            # Convert title string to Enum if possible
            qs_title = qs_data.title
            try:
                # Try to map string to Enum member
                qs_title = QuestionSetTitleEnum(qs_data.title)
            except ValueError:
                # Fallback to string if not a valid enum value (though model might reject it later)
                pass

            # Check if exists by title?
            qs = await self._get_or_create_by_name(
                db, QuestionSet, crud_question_set, QuestionSetCreate,
                qs_title, {}, user_id, lookup_field="title"
            )

            # Link to Exam Paper
            # Check for existing association first to be safe
            existing_link = await crud_exam_paper.check_existing_association_with_question_set(
                 db_session=db, exampaper=exam_paper, question_set=qs
            )
            
            if not existing_link:
                await crud_exam_paper.create_question_set_for_exam_paper(
                    db_session=db,
                    exam_paper_id=exam_paper.id,
                    question_set_id=qs.id
                )
            
            for mq_data in qs_data.main_questions:
                # Check if Main Question already exists
                existing_mq = await crud_question.get_existing_main_question(
                    db_session=db,
                    exam_paper_id=exam_paper.id,
                    question_set_id=qs.id,
                    question_number=mq_data.question_number
                )
                
                if existing_mq:
                    logger.info(f"Skipping main question {mq_data.question_number} (already exists). Skipping its sub-questions as well.")
                    continue

                # Create Main Question
                mq_in = MainQuestionCreate(
                    text=mq_data.text,
                    marks=mq_data.marks,
                    numbering_style=mq_data.numbering_style,
                    question_number=mq_data.question_number,
                    question_set_id=qs.id,
                    exam_paper_id=exam_paper.id
                )
                
                main_q = await crud_question.create(db_session=db, obj_in=mq_in, created_by_id=user_id)
                
                # Create Sub Questions
                for sq_data in mq_data.sub_questions:
                    sq_in = SubQuestionCreate(
                        text=sq_data.text,
                        marks=sq_data.marks,
                        numbering_style=sq_data.numbering_style,
                        question_number=sq_data.question_number,
                        parent_id=main_q.id
                        # exam_paper_id removed as it is not in SubQuestionCreate schema
                    )
                    await crud_question.create(db_session=db, obj_in=sq_in, created_by_id=user_id)

        await db.refresh(exam_paper)
        return exam_paper

exam_paper_builder_service = ExamPaperBuilderService()
