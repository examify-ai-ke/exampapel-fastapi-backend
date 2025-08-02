from uuid import UUID
from typing import Optional, Literal, Dict
from app.utils.search_utils import SearchQueryBuilder, SearchResultProcessor
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
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
from app.models.question_model import Question, QuestionSet
from app.models.exam_paper_model import ExamPaper
from app.models.answer_model import Answer
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.question_schema import (
    MainQuestionCreate,
    SubQuestionCreate,
    MainQuestionRead,
    SubQuestionRead,
    QuestionRead,
    MainQuestionUpdate,
    SubQuestionUpdate,
)
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
from sqlalchemy.orm import selectinload
from sqlmodel import select, and_, or_, col, func
from sqlalchemy import Text
from typing import Dict, List

router = APIRouter()

QuestionType = Literal["main", "sub", "all"]

@router.get("")
async def get_questions(
    question_type: QuestionType = Query(default="all", description="Filter by question type: main, sub, or all"),
    question_set_id: Optional[UUID] = Query(default=None, description="Filter by question set ID (for main questions)"),
    parent_id: Optional[UUID] = Query(default=None, description="Filter by parent question ID (for sub-questions)"),
    exam_paper_id: Optional[UUID] = Query(default=None, description="Filter by exam paper ID (for main questions)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[QuestionRead]:
    """
    Gets a paginated list of questions with flexible filtering
    
    - **question_type**: Filter by 'main', 'sub', or 'all' questions
    - **question_set_id**: Filter main questions by question set
    - **parent_id**: Filter sub-questions by parent question
    - **exam_paper_id**: Filter main questions by exam paper
    """
    
    # Build the query based on filters
    query = select(Question).options(
        selectinload(Question.question_set),
        selectinload(Question.exam_paper),
        selectinload(Question.parent),
        selectinload(Question.children).selectinload(Question.answers),
        selectinload(Question.answers),
        selectinload(Question.created_by),
    )
    
    # Apply type filtering
    if question_type == "main":
        query = query.where(Question.question_set_id.is_not(None))
        if question_set_id:
            query = query.where(Question.question_set_id == question_set_id)
        if exam_paper_id:
            query = query.where(Question.exam_paper_id == exam_paper_id)
    elif question_type == "sub":
        query = query.where(Question.parent_id.is_not(None))
        if parent_id:
            query = query.where(Question.parent_id == parent_id)
    # For "all", no additional filtering needed
    
    # Use the proper pagination method
    questions = await crud.question.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query,
        order=IOrderEnum.ascendent,
        order_by="question_number"
    )
    
    return create_response(data=questions)


@router.get("/search")
async def search_questions(
    q: str = Query(..., description="Search query for questions"),
    question_type: QuestionType = Query(default="all", description="Filter by question type"),
    exam_paper_id: Optional[UUID] = Query(default=None, description="Filter by exam paper ID"),
    question_set_id: Optional[UUID] = Query(default=None, description="Filter by question set ID"),
    marks_min: Optional[int] = Query(default=None, description="Minimum marks"),
    marks_max: Optional[int] = Query(default=None, description="Maximum marks"),
    numbering_style: Optional[str] = Query(default=None, description="Filter by numbering style"),
    has_answers: Optional[bool] = Query(default=None, description="Filter questions with/without answers"),
    sort_by: str = Query(default="relevance", description="Sort by: relevance, marks, created_at"),
    sort_order: str = Query(default="desc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    highlight: bool = Query(default=False, description="Enable search term highlighting"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[QuestionRead]:
    """
    Advanced search for questions with comprehensive filtering and sorting.
    
    Search across:
    - Question text content (JSON blocks)
    - Question slugs
    - Question numbers
    - Related exam paper and question set data
    
    Features:
    - Full-text search in question content
    - Multiple filtering options
    - Relevance-based sorting
    - Search result highlighting
    """
    
    # Build search conditions
    search_conditions = []
    
    if q:
        q_clean = q.strip()
        
        # Search in multiple fields
        text_conditions = [
            # Search in slug
            Question.slug.ilike(f"%{q_clean}%"),
            # Search in question number
            Question.question_number.ilike(f"%{q_clean}%"),
            # Search in JSON text content (cast to text for searching)
            func.cast(Question.text, Text).ilike(f"%{q_clean}%"),
        ]
        
        search_conditions.append(or_(*text_conditions))
    
    # Build filter conditions
    filter_conditions = []
    
    # Question type filtering
    if question_type == "main":
        filter_conditions.append(Question.question_set_id.is_not(None))
        filter_conditions.append(Question.parent_id.is_(None))
    elif question_type == "sub":
        filter_conditions.append(Question.parent_id.is_not(None))
    
    # Other filters
    if exam_paper_id:
        filter_conditions.append(Question.exam_paper_id == exam_paper_id)
    
    if question_set_id:
        filter_conditions.append(Question.question_set_id == question_set_id)
    
    if marks_min is not None:
        filter_conditions.append(Question.marks >= marks_min)
    
    if marks_max is not None:
        filter_conditions.append(Question.marks <= marks_max)
    
    if numbering_style:
        filter_conditions.append(Question.numbering_style == numbering_style)
    
    if has_answers is not None:
        if has_answers:
            # Questions that have answers
            filter_conditions.append(
                func.exists(
                    select(1).select_from(Answer).where(Answer.question_id == Question.id)
                )
            )
        else:
            # Questions without answers
            filter_conditions.append(
                ~func.exists(
                    select(1).select_from(Answer).where(Answer.question_id == Question.id)
                )
            )
    
    # Build the complete query
    query = select(Question).options(
        # Optimized loading for search results
        selectinload(Question.question_set).load_only(
            QuestionSet.id, QuestionSet.title, QuestionSet.slug
        ),
        selectinload(Question.exam_paper).load_only(
            ExamPaper.id, ExamPaper.year_of_exam
        ),
        selectinload(Question.parent).load_only(
            Question.id, Question.question_number, Question.slug
        ),
        selectinload(Question.created_by).load_only(
            User.id, User.first_name, User.last_name, User.email
        ),
        # Load answers count for context
        selectinload(Question.answers).load_only(
            Answer.id, Answer.likes, Answer.dislikes, Answer.reviewed
        ),
    )
    
    # Apply search conditions
    if search_conditions:
        query = query.where(and_(*search_conditions))
    
    # Apply filter conditions
    if filter_conditions:
        query = query.where(and_(*filter_conditions))
    
    # Apply sorting
    if sort_by == "marks":
        sort_field = Question.marks
    elif sort_by == "created_at":
        sort_field = Question.created_at
    else:  # relevance or default
        # For relevance, we'll sort by a combination of factors
        sort_field = Question.created_at  # Default fallback
    
    if sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())
    
    # Execute paginated query
    questions = await crud.question.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query
    )
    
    return create_response(data=questions)


@router.get("/search/suggestions")
async def get_question_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    question_type: QuestionType = Query(default="all", description="Filter suggestions by question type"),
    limit: int = Query(default=10, ge=1, le=20),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[List[Dict[str, str]]]:
    """
    Get search suggestions for questions based on partial input.
    
    Returns suggestions from:
    - Question numbers
    - Question slugs
    """
    
    suggestions = []
    q_clean = q.strip().lower()
    
    # Question number suggestions
    number_query = (
        select(Question.question_number)
        .where(Question.question_number.ilike(f"%{q_clean}%"))
        .distinct()
        .limit(5)
    )
    
    # Apply question type filter
    if question_type == "main":
        number_query = number_query.where(Question.question_set_id.is_not(None))
    elif question_type == "sub":
        number_query = number_query.where(Question.parent_id.is_not(None))
    
    number_result = await db_session.execute(number_query)
    for (question_number,) in number_result.all():
        if question_number:
            suggestions.append({
                "type": "question_number",
                "value": question_number,
                "display": f"Question {question_number}"
            })
    
    # Question slug suggestions
    slug_query = (
        select(Question.slug)
        .where(Question.slug.ilike(f"%{q_clean}%"))
        .distinct()
        .limit(5)
    )
    
    # Apply question type filter
    if question_type == "main":
        slug_query = slug_query.where(Question.question_set_id.is_not(None))
    elif question_type == "sub":
        slug_query = slug_query.where(Question.parent_id.is_not(None))
    
    slug_result = await db_session.execute(slug_query)
    for (slug,) in slug_result.all():
        if slug:
            suggestions.append({
                "type": "slug",
                "value": slug,
                "display": f"Slug: {slug}"
            })
    
    # Limit total suggestions
    suggestions = suggestions[:limit]
    
    return create_response(data=suggestions)


@router.get("/{question_id}")
async def get_question_by_id(
    question_id: UUID,
    include_children: bool = Query(default=True, description="Include sub-questions in response"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[QuestionRead]:
    """
    Gets a question by its ID (works for both main and sub questions)
    """
    if include_children:
        question = await crud.question.get_question_with_children(
            question_id=question_id,
            db_session=db_session
        )
    else:
        question = await crud.question.get(id=question_id, db_session=db_session)
    
    if not question:
        raise IdNotFoundException(Question, question_id)

    return create_response(data=question)


@router.get("/{question_id}/sub-questions")
async def get_sub_questions_for_question(
    question_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[SubQuestionRead]:
    """
    Gets all sub-questions for a specific main question
    """
    # Build query for sub-questions of the specific parent
    query = (
        select(Question)
        .where(Question.parent_id == question_id)
        .options(
            selectinload(Question.parent),
            selectinload(Question.answers),
            selectinload(Question.created_by),
        )
    )
    
    # Use proper pagination method
    sub_questions = await crud.question.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query,
        order=IOrderEnum.ascendent,
        order_by="question_number"
    )
    
    return create_response(data=sub_questions)


@router.post("/main")
async def create_main_question(
    question: MainQuestionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[MainQuestionRead]:
    """
    Creates a new main question
    
    Required roles:
    - admin
    - manager
    """
    created_question = await crud.question.create(
        obj_in=question, 
        created_by_id=current_user.id,
        db_session=db_session
    )
    return create_response(data=created_question)


@router.post("/sub")
async def create_sub_question(
    question: SubQuestionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[SubQuestionRead]:
    """
    Creates a new sub-question
    
    Required roles:
    - admin
    - manager
    """
    created_question = await crud.question.create(
        obj_in=question, 
        created_by_id=current_user.id,
        db_session=db_session
    )
    return create_response(data=created_question)


@router.put("/{question_id}")
async def update_question(
    question_id: UUID,
    question: MainQuestionUpdate | SubQuestionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[QuestionRead]:
    """
    Updates a question by its ID (works for both main and sub questions)
    
    Required roles:
    - admin
    - manager
    """
    current_question = await crud.question.get(id=question_id, db_session=db_session)
    if not current_question:
        raise IdNotFoundException(Question, question_id)
    
    updated_question = await crud.question.update(
        obj_current=current_question,
        obj_new=question,
        db_session=db_session
    )
    
    return create_response(data=updated_question)


@router.delete("/{question_id}")
async def delete_question(
    question_id: UUID,
    cascade: bool = Query(default=True, description="Delete sub-questions if this is a main question"),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[QuestionRead]:
    """
    Deletes a question by its ID (works for both main and sub questions)
    
    Required roles:
    - admin
    - manager
    """
    if cascade:
        deleted_question = await crud.question.delete_question_cascade(
            question_id=question_id,
            db_session=db_session
        )
    else:
        deleted_question = await crud.question.remove(id=question_id, db_session=db_session)
        if not deleted_question:
            raise IdNotFoundException(Question, question_id)
    
    return create_response(data=deleted_question)


@router.post("/{question_id}/sub-questions/bulk")
async def create_multiple_sub_questions(
    question_id: UUID,
    sub_questions: list[SubQuestionCreate],
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[list[SubQuestionRead]]:
    """
    Creates multiple sub-questions for a main question
    
    Required roles:
    - admin
    - manager
    """
    created_questions = await crud.question.bulk_create_sub_questions(
        parent_id=question_id,
        sub_questions=sub_questions,
        created_by_id=current_user.id,
        db_session=db_session
    )
    
    return create_response(data=created_questions)


@router.get("/stats")
async def get_question_statistics(
    question_set_id: Optional[UUID] = Query(default=None, description="Filter by question set"),
    exam_paper_id: Optional[UUID] = Query(default=None, description="Filter by exam paper"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[dict]:
    """
    Get statistics about questions
    """
    main_count = await crud.question.count_questions_by_type(
        question_type="main",
        question_set_id=question_set_id,
        db_session=db_session
    )
    
    sub_count = await crud.question.count_questions_by_type(
        question_type="sub",
        db_session=db_session
    )
    
    total_count = await crud.question.count_questions_by_type(
        question_type="all",
        db_session=db_session
    )
    
    stats = {
        "total_questions": total_count,
        "main_questions": main_count,
        "sub_questions": sub_count,
        "average_sub_questions_per_main": round(sub_count / main_count, 2) if main_count > 0 else 0
    }
    
    return create_response(data=stats)


