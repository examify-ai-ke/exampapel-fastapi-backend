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
from app.models.question_model import MainQuestion, QuestionSet
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.question_schema import (
    QuestionSetCreate,
    QuestionSetRead,
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
    Gets a paginated list of question sets
    """
    query = (
        select(QuestionSet)
        .options(
            selectinload(QuestionSet.exam_papers),  # Load related exam paper
            selectinload(QuestionSet.main_questions),  # Load related questions
            selectinload(QuestionSet.created_by),  # Load creator details
        )
        .offset(skip)
        .limit(limit)
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
    Gets a QuestionSet by its id with all related entities.
    """
    options = [
        selectinload(QuestionSet.exam_papers),  # Load related exam papers
        selectinload(QuestionSet.main_questions)
        .selectinload(MainQuestion.subquestions),  # Load main questions and their subquestions
        selectinload(QuestionSet.main_questions)
        .selectinload(MainQuestion.answers),  # Load answers for main questions
        selectinload(QuestionSet.created_by),  # Load creator details
    ]

    question_set = await crud.question_set.get(
        id=question_set_id, db_session=db_session
    )
    if not question_set:
        raise IdNotFoundException(QuestionSet, question_set_id)

    return create_response(data=question_set)


@router.post("")
async def create_question_set(
    quizset: QuestionSetCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[QuestionSetRead]:
    """
    Creates a new QuestionSet

    Required roles:
    - admin
    - manager
    """

    quiz = await crud.question_set.create(
        obj_in=quizset, created_by_id=current_user.id
    )
    return create_response(data=quiz)


@router.put("/{question_set_id}")
async def update_question_set(
    question_set_id: UUID,
    questionset: QuestionSetUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[QuestionSetRead]:
    """
    Updates a QuestionSet by its id

    Required roles:
    - admin
    - manager
    """
    question_set = await crud.question_set.get(id=question_set_id)
    if not question_set:
        raise IdNotFoundException(QuestionSet, question_set_id)
    # if not is_authorized(current_user, "read", current_programme):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this QuestionSet because you did not created it",
    #     )

    quiz_updated = await crud.question_set.update(
        obj_new=questionset, obj_current=question_set
    )
    return create_response(data=quiz_updated)


@router.delete("/{question_set_id}")
async def remove_question_set(
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[QuestionSetRead]:
    """
    Deletes a QuestionSet by its id

    Required roles:
    - admin
    - manager
    """
    current_quiz = await crud.question_set.get(id=question_set_id)
    if not current_quiz:
        raise IdNotFoundException(QuestionSet, question_set_id)
    quiz = await crud.question_set.remove(id=question_set_id)
    return create_response(data=quiz)


# Associate  programme with departmenmt
# @router.post("/{programme_id}/courses/{course_id}")
# async def add_course_to_programme(
#     programme_id: UUID,
#     course_id: UUID,
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
# ) -> IPostResponseBase[ProgrammeRead]:
#     """
#     Add a Course to a Programme by Ids

#     Required roles:
#     - admin
#     - manager
#     """
#     course_db = await crud.course.get(id=course_id)
#     programme_db = await crud.programme.get(id=programme_id)
#     if not course_db or not programme_db:
#         raise HTTPException(
#             status_code=404, detail="Programme  or Course not found"
#         )

#     # Check if association already exist
#     _association = await crud.course.check_existing_association_with_programme(
#         course=course_db, programme=programme_db
#     )

#     if _association is not None:
#         # If an association already exists, raise an error or return a suitable response
#         raise HTTPException(
#             status_code=400,
#             detail=f"Course '{course_db.name}' is already associated with Programme '{programme_db.name}'",
#         )
#     else:
#         # Add the programme to the department's list of programmes
#         programme_db.courses.append(course_db)

#         department_with_programme = await crud.department.add_related(
#             appended_parent_object=programme_db
#         )
#         return create_response(data=department_with_programme)
