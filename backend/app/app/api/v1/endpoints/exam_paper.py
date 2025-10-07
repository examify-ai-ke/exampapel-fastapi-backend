from uuid import UUID
from typing import Dict
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.question_model import QuestionSet, Question
from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.minio_client import MinioClient
from fastapi_pagination import Params
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)
from app import crud
from app.api import deps
from app.models.exam_paper_model import ExamPaper, ExamInstruction, ExamPaperQuestionLink, ExamTitle, ExamDescription
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.models.answer_model import Answer
from app.schemas.exam_paper_schema import (
    ExamPaperCreate,
    ExamPaperRead,
    ExamPaperUpdate,
    InstructionCreate,
    InstructionRead,
    InstructionUpdate
)
# from app.schemas.exam_paper_simple_schema import ExamPaperSimpleRead
from app.schemas.response_schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    create_response,
)
from app.schemas.role_schema import IRoleEnum
from app.core.authz import is_authorized
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import select
from app.utils.search_utils import SearchQueryBuilder, SearchResultProcessor
from sqlalchemy import or_, and_, func, delete
from datetime import date
from app.models.course_model import Course
from app.models.institution_model import Institution
from typing import Dict, List

router = APIRouter()


@router.get("")
async def get_exam_paper_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of exam papers with ultra-optimized loading
    """
    # Ultra-optimized query - minimal data loading for maximum performance
    query = (
        select(ExamPaper).options(
            # Use joinedload for many-to-one relationships (more efficient)
            joinedload(ExamPaper.course).load_only(
                Course.id, Course.name, Course.course_acronym, Course.slug
            ),
            joinedload(ExamPaper.institution).load_only(
                Institution.id, Institution.name, Institution.slug
            ),
            joinedload(ExamPaper.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            # Don't load question_sets, modules, instructions - use count properties
        )
    )
    exam_papers = await crud.exam_paper.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=exam_papers)
@router.get("/search")
async def search_exam_papers(
    q: str = Query(default=None, description="Search query for exam papers"),
    year: str = Query(default=None, description="Filter by exam year"),
    course_id: UUID = Query(default=None, description="Filter by course ID"),
    institution_id: UUID = Query(default=None, description="Filter by institution ID"),
    exam_date_from: date = Query(default=None, description="Filter exams from this date"),
    exam_date_to: date = Query(default=None, description="Filter exams to this date"),
    duration_min: int = Query(default=None, description="Minimum exam duration in minutes"),
    duration_max: int = Query(default=None, description="Maximum exam duration in minutes"),
    tags: str = Query(default=None, description="Filter by tags (comma-separated)"),
    sort_by: str = Query(default="relevance", description="Sort by: relevance, date, duration, title"),
    sort_order: str = Query(default="desc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    highlight: bool = Query(default=False, description="Enable search term highlighting"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Advanced search for exam papers with multiple filters and sorting options.
    
    Search across:
    - Exam paper identifying names
    - Course names and acronyms
    - Institution names
    - Exam descriptions and titles
    - Tags
    
    Features:
    - Full-text search with relevance scoring
    - Date range filtering
    - Duration range filtering
    - Tag-based filtering
    - Multiple sorting options
    - Search result highlighting
    """
    
    # Build the base query with optimized loading
    builder = SearchQueryBuilder(ExamPaper, db_session)
    
    # Add search fields for comprehensive search
    search_fields = [
        ExamPaper.year_of_exam,
    ]
    builder.add_search_fields(*search_fields)
    
    # Build advanced search conditions
    search_conditions = []
    
    if q:
        # Multi-field search with different strategies
        q_clean = q.strip()
        
        # Direct field searches (only actual database columns)
        direct_conditions = [
            ExamPaper.year_of_exam.ilike(f"%{q_clean}%"),
        ]
        
        # Related model searches (using joins)
        related_conditions = [
            # Search in course
            Course.name.ilike(f"%{q_clean}%"),
            Course.course_acronym.ilike(f"%{q_clean}%"),
            # Search in institution
            Institution.name.ilike(f"%{q_clean}%"),
        ]
        
        # Combine all search conditions
        search_conditions.extend(direct_conditions + related_conditions)
    
    # Apply filters
    filters = []
    
    if year:
        filters.append(ExamPaper.year_of_exam == year)
    
    if course_id:
        filters.append(ExamPaper.course_id == course_id)
    
    if institution_id:
        filters.append(ExamPaper.institution_id == institution_id)
    
    if exam_date_from:
        filters.append(ExamPaper.exam_date >= exam_date_from)
    
    if exam_date_to:
        filters.append(ExamPaper.exam_date <= exam_date_to)
    
    if duration_min:
        filters.append(ExamPaper.exam_duration >= duration_min)
    
    if duration_max:
        filters.append(ExamPaper.exam_duration <= duration_max)
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        for tag in tag_list:
            tag_condition = func.jsonb_array_elements_text(ExamPaper.tags).ilike(f"%{tag}%")
            filters.append(func.exists(select(1).where(tag_condition)))
    
    # Build the complete query
    query = (
        select(ExamPaper)
        .join(Course, ExamPaper.course_id == Course.id, isouter=True)
        .join(Institution, ExamPaper.institution_id == Institution.id, isouter=True)
        .options(
            # Optimized loading for search results
            joinedload(ExamPaper.course).load_only(
                Course.id, Course.name, Course.course_acronym, Course.slug
            ),
            joinedload(ExamPaper.institution).load_only(
                Institution.id, Institution.name, Institution.slug
            ),
            joinedload(ExamPaper.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            # Load minimal related data for search context
            selectinload(ExamPaper.title).load_only(
                ExamTitle.id, ExamTitle.name, ExamTitle.slug
            ),
            selectinload(ExamPaper.description).load_only(
                ExamDescription.id, ExamDescription.name, ExamDescription.slug
            ),
            # Eagerly load nested question relationships to prevent MissingGreenlet
            selectinload(ExamPaper.question_sets)
            .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
            .selectinload(Question.children),
            selectinload(ExamPaper.question_sets)
            .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
            .selectinload(Question.answers),
            selectinload(ExamPaper.instructions),
            selectinload(ExamPaper.modules),
        )
    )
    
    # Combine search conditions and filters properly
    all_conditions = []
    
    # Add search conditions (if any)
    if search_conditions:
        all_conditions.append(or_(*search_conditions))
    
    # Add filter conditions (if any)
    if filters:
        all_conditions.extend(filters)
    
    # Apply all conditions
    if all_conditions:
        if len(all_conditions) == 1:
            query = query.where(all_conditions[0])
        else:
            # If we have both search and filters, combine them with AND
            query = query.where(and_(*all_conditions))
    
    # Apply sorting
    if sort_by == "date":
        sort_field = ExamPaper.exam_date
    elif sort_by == "duration":
        sort_field = ExamPaper.exam_duration
    elif sort_by == "title":
        # Since identifying_name is a property, we'll sort by year_of_exam instead
        sort_field = ExamPaper.year_of_exam
    else:  # relevance or default
        # For relevance, we'll sort by created_at desc as a proxy
        sort_field = ExamPaper.created_at
    
    if sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())
    
    # Execute paginated query
    exam_papers = await crud.exam_paper.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    
    # Add search metadata if highlighting is enabled
    if highlight and q:
        # This would be implemented in the response processing
        # For now, we'll return the standard response
        pass
    
    return create_response(data=exam_papers)


@router.get("/search/suggestions")
async def get_exam_paper_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(default=10, ge=1, le=20),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[List[Dict[str, str]]]:
    """
    Get search suggestions for exam papers based on partial input.
    
    Returns suggestions from:
    - Course names
    - Institution names
    - Exam years
    - Common tags
    """
    
    suggestions = []
    q_clean = q.strip().lower()
    
    # Course name suggestions
    course_query = (
        select(Course.name, Course.course_acronym)
        .where(
            or_(
                Course.name.ilike(f"%{q_clean}%"),
                Course.course_acronym.ilike(f"%{q_clean}%")
            )
        )
        .limit(5)
    )
    course_result = await db_session.execute(course_query)
    for course_name, acronym in course_result.all():
        suggestions.append({
            "type": "course",
            "value": course_name,
            "display": f"{course_name} ({acronym})" if acronym else course_name
        })
    
    # Institution name suggestions
    institution_query = (
        select(Institution.name)
        .where(Institution.name.ilike(f"%{q_clean}%"))
        .limit(5)
    )
    institution_result = await db_session.execute(institution_query)
    for (institution_name,) in institution_result.all():
        suggestions.append({
            "type": "institution",
            "value": institution_name,
            "display": institution_name
        })
    
    # Year suggestions
    year_query = (
        select(ExamPaper.year_of_exam)
        .where(ExamPaper.year_of_exam.ilike(f"%{q_clean}%"))
        .distinct()
        .limit(3)
    )
    year_result = await db_session.execute(year_query)
    for (year,) in year_result.all():
        if year:
            suggestions.append({
                "type": "year",
                "value": year,
                "display": f"Year {year}"
            })
    
    # Limit total suggestions
    suggestions = suggestions[:limit]
    
    return create_response(data=suggestions)


async def get_exam_paper_properties(
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
    ):
    exam_headers= await crud.exam_paper.get_all_exam_properties(db_session=db_session)
    return exam_headers


@router.get("/get_by_created_at")
async def get_exams_list_order_by_created_at(
    order: IOrderEnum = Query(
        default=IOrderEnum.descendent, description="Sort order: ascendent or descendent"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of ExamPapers ordered by created_at datetime
    """
    query = (
        select(ExamPaper)
        .options(
            selectinload(ExamPaper.course),
            selectinload(ExamPaper.description),
            selectinload(ExamPaper.institution),
            selectinload(ExamPaper.title),
            selectinload(ExamPaper.modules),
            selectinload(ExamPaper.instructions),
            selectinload(ExamPaper.created_by),
        )
    )
    
    exampapers = await crud.exam_paper.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query,
        order=order,
        order_by="created_at"
    )
    return create_response(data=exampapers)


@router.get("/get_by_id/{exampaper_id}")
async def get_exam_paper_by_id(
    exampaper_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[ExamPaperRead]:
    """
    Get an ExamPaper by ID with all related modules and nested relationships.
    """
    options = [
        selectinload(ExamPaper.course),  # Load related course
        selectinload(ExamPaper.description),  # Load related exam description
        selectinload(ExamPaper.institution),  # Load related institution
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(
            Question.children  # Load main questions and their sub-questions
        ),
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(Question.answers),  # Load answers for main questions
        selectinload(ExamPaper.created_by),  # Load creator details
        selectinload(ExamPaper.instructions),  # Load related instructions
        selectinload(ExamPaper.modules),  # Load related modules
        selectinload(ExamPaper.title),  # Load related exam title
    ]

    exampaper = await crud.exam_paper.get(
        id=exampaper_id, db_session=db_session, options=options
    )
    if not exampaper:
        raise IdNotFoundException(ExamPaper, exampaper_id)

    # print_hero.delay(hero.id)
    return create_response(data=exampaper)


@router.get("/get_by_slug/{exampaper_slug}")
async def get_exam_paper_by_slug(
    exampaper_slug: str,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[ExamPaperRead]:
    """
    Gets a ExamPaper by slug with all related data
    """
    exampaper = await crud.exam_paper.get_exam_paper_by_slug(
        slug=exampaper_slug, db_session=db_session
    )
    if not exampaper:
        raise NameNotFoundException(ExamPaper, exampaper_slug)

    # Load all relationships to match the schema
    options = [
        selectinload(ExamPaper.course),
        selectinload(ExamPaper.description),
        selectinload(ExamPaper.institution),
        selectinload(ExamPaper.title),
        selectinload(ExamPaper.modules),
        selectinload(ExamPaper.instructions),
        selectinload(ExamPaper.created_by),
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(Question.children),
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(Question.answers),
    ]
    
    # Reload with all relationships
    exampaper_full = await crud.exam_paper.get(
        id=exampaper.id, db_session=db_session, options=options
    )

    return create_response(data=exampaper_full)


@router.post("")
async def create_exam_paper(
    exampaper: ExamPaperCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ExamPaperRead]:
    """
    Creates a new ExamPaper

    Required roles:
    - admin
    - manager
    """

    instructions = await crud.instruction.get_by_ids(list_ids=exampaper.instruction_ids)
    modules = await crud.module.get_by_ids(list_ids=exampaper.module_ids)
    # course = await crud.course.get(id=exampaper.course_id)
    if len(instructions) != len(exampaper.instruction_ids):
        raise HTTPException(
            status_code=404, detail="Some instructions not found"
        )
    if len(modules) != len(exampaper.module_ids):
        raise HTTPException(status_code=404, detail="Some modules not found")
    # if not course:
    #     raise HTTPException(status_code=404, detail="The Selected Course was not found")
    # Add modules to the examPaper
    # exampaper..modules.extend(modules_list)  # Add the list of modules
    
    exampaper = await crud.exam_paper.create_with_related_list(
        obj_in=exampaper,
        related_list_object1=instructions,
        related_list_object2=modules,
        # related_object3=course,
        items1="instructions",
        items2="modules",
        created_by_id=current_user.id,
    )
    return create_response(data=exampaper)


@router.put("/{exampaper_id}")
async def update_exam_paper(
    exampaper_id: UUID,
    exampaper_new: ExamPaperUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[ExamPaperRead]:
    """
    Updates a ExamPaper by its id

    Required roles:
    - admin
    - manager
    """
    exam_updated = await crud.exam_paper.update_examPaper(
        exam_paper_id=exampaper_id, obj_new=exampaper_new, db_session=db_session
    )

  

    return create_response(data=exam_updated)


@router.delete("/{exampaper_id}")
async def remove_exam_paper(
    exampaper_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ExamPaperRead]:
    """
    Deletes a ExamPaper by its id

    Required roles:
    - admin
    - manager
    """
    current_exam = await crud.exam_paper.get(id=exampaper_id)
    if not current_exam:
        raise IdNotFoundException(ExamPaper, exampaper_id)
    exam = await crud.exam_paper.remove(id=exampaper_id)
    return create_response(data=exam)


# # Associate ExamPaper with A QuestionSet
@router.post("/{exampaper_id}/question-sets/{question_set_id}")
async def add_question_set_to_exam_paper(
    exampaper_id: UUID,
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[ExamPaperRead]:
    """
    Add a QuestionSet to an ExamPaper by IDs.

    Required roles:
    - admin
    - manager
    """
    # Fetch the ExamPaper
    exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)
    if not exam_paper:
        raise HTTPException(status_code=404, detail="ExamPaper not found")

    # Fetch the QuestionSet
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise HTTPException(status_code=404, detail="QuestionSet not found")

    # Check if the QuestionSet is already associated with the ExamPaper
    if question_set.id in [qs.id for qs in exam_paper.question_sets]:
        raise HTTPException(
            status_code=400,
            detail=f"ExamPaper '{exam_paper.year_of_exam}-{exam_paper.title.name}-{exam_paper.description.name}' is already associated with QuestionSet '{question_set.title}'",
        )

    # Add the QuestionSet to the ExamPaper
    exam_paper.question_sets.append(question_set)

    # Save the updated ExamPaper
    updated_exam_paper = await crud.exam_paper.update(
        obj_current=exam_paper, obj_new=exam_paper, db_session=db_session
    )

    return create_response(data=updated_exam_paper)


@router.delete("/{exampaper_id}/question-sets/{question_set_id}")
async def remove_question_set_from_exam_paper(
    exampaper_id: UUID,
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[ExamPaperRead]:
    """
    Remove a QuestionSet from an ExamPaper by IDs without deleting the QuestionSet.

    Required roles:
    - admin
    - manager
    """
    # Fetch the ExamPaper
    exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)
    if not exam_paper:
        raise HTTPException(status_code=404, detail="ExamPaper not found")

    # Fetch the QuestionSet
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise HTTPException(status_code=404, detail="QuestionSet not found")

    # Check if the QuestionSet is associated with the ExamPaper
    if question_set.id not in [qs.id for qs in exam_paper.question_sets]:
        raise HTTPException(
            status_code=400,
            detail=f"QuestionSet '{question_set.title}' is not associated with ExamPaper '{exam_paper.year_of_exam}-{exam_paper.title.name}-{exam_paper.description.name}'",
        )

    # Unlink the QuestionSet from the ExamPaper by deleting the association in the linking table
    await db_session.execute(
        delete(ExamPaperQuestionLink).where(
            ExamPaperQuestionLink.exam_id == exampaper_id,
            ExamPaperQuestionLink.question_set_id == question_set_id,
        )
    )
    await db_session.commit()

    # Fetch the updated ExamPaper to return in the response
    updated_exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)

    return create_response(data=updated_exam_paper)
