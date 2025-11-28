from typing import List
from uuid import UUID
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
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.question_schema import (
    QuestionRead,
    QuestionSetCreate,
    QuestionSetRead,
    QuestionSetReadWithQuestions,
    QuestionSetUpdate,
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
from sqlmodel import select

router = APIRouter()


@router.get("")
async def get_question_set_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[QuestionSetRead]:
    """
    Gets a paginated list of question sets with stats only (no full questions)
    """
    from app.models.user_model import User
    
    # Ultra-lightweight query - only load counts, no questions or answers
    query = (
        select(QuestionSet)
        .options(
            selectinload(QuestionSet.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            )
            # Don't load questions - use count properties instead
        )
    )
    q_sets = await crud.question_set.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query,
        order=IOrderEnum.ascendent, order_by="title"
    )
    return create_response(data=q_sets)


@router.get("/get_by_id/{question_set_id}")
async def get_question_set_by_id(
    question_set_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[QuestionSetRead]:
    """
    Gets a QuestionSet by its id with stats only.
    """
    from app.models.user_model import User
    
    # Lightweight query - only load counts, no questions
    query = (
        select(QuestionSet)
        .where(QuestionSet.id == question_set_id)
        .options(
            selectinload(QuestionSet.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            )
        )
    )

    result = await db_session.execute(query)
    question_set = result.unique().scalar_one_or_none()
    
    if not question_set:
        raise IdNotFoundException(QuestionSet, question_set_id)

    return create_response(data=question_set)


@router.get("/{question_set_id}/questions")
async def get_questions_by_question_set(
    question_set_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[QuestionRead]:
    """
    Gets all main questions for a specific question set
    """
    from app.schemas.question_schema import QuestionRead
    from app.models.user_model import User
    
    # Verify question set exists
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise IdNotFoundException(QuestionSet, question_set_id)

    # Build optimized query for main questions
    query = (
        select(Question)
        .where(
            Question.question_set_id == question_set_id,
            Question.parent_id.is_(None)  # Main questions only
        )
        .options(
            selectinload(Question.question_set),
            selectinload(Question.exam_paper),
            selectinload(Question.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Question.answers),
            selectinload(Question.children).selectinload(Question.answers)
        )
        .order_by(Question.question_number)
    )
    
    # Get paginated results
    main_questions = await crud.question.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        query=query
    )
    
    return create_response(data=main_questions)


@router.post("")
async def create_question_set(
    quizset: QuestionSetCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[QuestionSetRead]:
    """
    Creates a new QuestionSet

    Required roles:
    - admin
    - manager
    """

    quiz = await crud.question_set.create(
        obj_in=quizset, created_by_id=current_user.id, db_session=db_session
    )
    return create_response(data=quiz)


@router.put("/{question_set_id}")
async def update_question_set(
    question_set_id: UUID,
    questionset: QuestionSetUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[QuestionSetRead]:
    """
    Updates a QuestionSet by its id

    Required roles:
    - admin
    - manager
    """
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise IdNotFoundException(QuestionSet, question_set_id)

    quiz_updated = await crud.question_set.update(
        obj_new=questionset, obj_current=question_set, db_session=db_session
    )
    return create_response(data=quiz_updated)


@router.delete("/{question_set_id}")
async def remove_question_set(
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[QuestionSetRead]:
    """
    Deletes a QuestionSet by its id

    Required roles:
    - admin
    - manager
    """
    current_quiz = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not current_quiz:
        raise IdNotFoundException(QuestionSet, question_set_id)
    quiz = await crud.question_set.remove(id=question_set_id, db_session=db_session)
    return create_response(data=quiz)

@router.get("/by-exam-paper/{exam_paper_id}")
async def get_question_sets_by_exam_paper(
    exam_paper_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[List[QuestionSetReadWithQuestions]]:
    """
    Gets all QuestionSets that belong to a specific exam paper with main and sub-questions
    """
    from app.models.user_model import User
    from app.models.exam_paper_model import ExamPaper
    from app.models.answer_model import Answer
    
    # Get exam paper with its question sets and all questions
    exam_paper = await crud.exam_paper.get(
        id=exam_paper_id,
        db_session=db_session,
        options=[
            selectinload(ExamPaper.question_sets).options(
                selectinload(QuestionSet.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                selectinload(QuestionSet.questions.and_(Question.exam_paper_id == exam_paper_id)).options(
                    selectinload(Question.answers).selectinload(Answer.created_by),
                    selectinload(Question.children).options(
                        selectinload(Question.answers).selectinload(Answer.created_by)
                    )
                )
            )
        ]
    )
    
    if not exam_paper:
        raise IdNotFoundException(ExamPaper, exam_paper_id)
    
    # Return the question sets from the exam paper
    return create_response(data=exam_paper.question_sets)