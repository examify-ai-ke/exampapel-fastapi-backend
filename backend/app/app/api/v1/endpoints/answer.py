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
from app.models.answer_model import Answer
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.answer_schema import (
    AnswerRead,
    AnswerCreate,
    AnswerUpdate,
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

router = APIRouter()


@router.get("")
async def get_answer_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[AnswerRead]:
    """
    Gets a paginated list of Answers
    """
    answers = await crud.answer.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit
    )
    return create_response(data=answers)


@router.get("/get_by_created_at")
async def get_answers_list_order_by_created_at(
    order: IOrderEnum | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[AnswerRead]:
    """
    Gets a paginated list of answers ordered by created at datetime
    """
    answers = await crud.answer.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=answers)


@router.get("/get_by_id/{answer_id}")
async def get_answer_by_id(
    answer_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[AnswerRead]:
    """
    Gets a answer by its id
    """
    answer = await crud.answer.get(id=answer_id)
    if not answer:
        raise IdNotFoundException(Answer, answer_id)
    return create_response(data=answer)

@router.post("")
async def create_answer(
    answer: AnswerCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[AnswerRead]:
    """
    Creates a new Answer

    Required roles:
    - admin
    - manager
    """

    _answer = await crud.answer.create(obj_in=answer, created_by_id=current_user.id)
    return create_response(data=_answer)


@router.put("/{answer_id}")
async def update_answer(
    answer_id: UUID,
    answer: AnswerUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[AnswerRead]:
    """
    Updates a Answer by its id

    Required roles:
    - admin
    - manager
    """
    current_answer= await crud.answer.get(id=answer_id)
    if not current_answer:
        raise IdNotFoundException(Answer, answer_id)
    if not is_authorized(current_user, "read", current_answer):
        raise HTTPException(
            status_code=403,
            detail="You are not Authorized to update this Answer because you did not created it",
        )

    answer_updated = await crud.answer.update(
        obj_new=answer, obj_current=current_answer
    )
    return create_response(data=answer_updated)


@router.delete("/{answer_id}")
async def remove_answer(
    answer_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[AnswerRead]:
    """
    Deletes a Answer by its id.
    Required roles:
    - admin
    - manager
    """
    current_answer = await crud.answer.get(id=answer_id)
    if not current_answer:
        raise IdNotFoundException(Answer, answer_id)
    answer = await crud.answer.remove(id=answer_id)
    return create_response(data=answer)
