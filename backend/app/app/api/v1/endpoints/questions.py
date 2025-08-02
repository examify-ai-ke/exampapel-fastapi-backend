from uuid import UUID
from typing import Optional, Literal
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
from app.models.question_model import Question
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
from sqlmodel import select, and_, or_, col

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


@router.get("/search")
async def search_questions(
    q: str = Query(..., description="Search query for question slug/text"),
    question_type: QuestionType = Query(default="all", description="Filter by question type"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[QuestionRead]:
    """
    Search questions by slug or text content
    """
    # Build search query
    query = (
        select(Question)
        .where(col(Question.slug).ilike(f"%{q}%"))
        .options(
            selectinload(Question.question_set),
            selectinload(Question.exam_paper),
            selectinload(Question.parent),
            selectinload(Question.children).selectinload(Question.answers),
            selectinload(Question.answers),
            selectinload(Question.created_by),
        )
    )
    
    # Apply type filtering
    if question_type == "main":
        query = query.where(Question.question_set_id.is_not(None))
    elif question_type == "sub":
        query = query.where(Question.parent_id.is_not(None))
    
    # Use proper pagination method
    questions = await crud.question.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query,
        order=IOrderEnum.ascendent,
        order_by="question_number"
    )
    
    return create_response(data=questions)


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
