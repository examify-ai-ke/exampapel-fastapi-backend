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
from app.models.question_model import SubQuestion
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.question_schema import (
    SubQuestionCreate,
    SubQuestionRead,
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


router = APIRouter()


@router.get("")
async def get_sub_question_list(
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[SubQuestionRead]:
    """
    Gets a paginated list of SubQuestion
    """
    questions = await crud.sub_question.get_multi_paginated(params=params)
    return create_response(data=questions)


# @router.get("/get_by_created_at")
# async def get_programme_list_order_by_created_at(
#     order: IOrderEnum
#     | None = Query(
#         default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
#     ),
#     params: Params = Depends(),
#     current_user: User = Depends(deps.get_current_user()),
# ) -> IGetResponsePaginated[ProgrammeRead]:
#     """
#     Gets a paginated list of programmes ordered by created at datetime
#     """
#     programmes = await crud.programme.get_multi_paginated_ordered(
#         params=params, order=order
#     )
#     return create_response(data=programmes)


@router.get("/get_by_id/{sub_question_id}")
async def get_sub_question_by_id(
    sub_question_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[SubQuestionRead]:
    """
    Gets a SubQuestion by its id
    """
    question = await crud.sub_question.get(id=sub_question_id)
    if not question:
        raise IdNotFoundException(SubQuestion, sub_question_id)

    # print_hero.delay(hero.id)
    return create_response(data=question)


# @router.get("/get_by_slug/{question_set_slug}")
# async def get_question_set_by_slug(
#     question_set_slug: str,
#     current_user: User = Depends(deps.get_current_user()),
# ) -> IGetResponseBase[list[QuestionSetRead]]:
#     """
#     Gets a QuestionSet by slug
#     """
#     quiz_set = await crud.question_set.get_question_by_slug(slug=programme_slug)
#     if not programme:
#         raise NameNotFoundException(Programme, programme_slug)

#     return create_response(data=programme)


@router.post("")
async def create_sub_question(
    question: SubQuestionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[SubQuestionRead]:
    """
    Creates a new SubQuestion

    Required roles:
    - admin
    - manager
    """

    quiz = await crud.sub_question.create(
        obj_in=question, created_by_id=current_user.id
    )
    return create_response(data=quiz)


@router.put("/{sub_question_id}")
async def update_sub_question(
    sub_question_id: UUID,
    sub_question: SubQuestionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[SubQuestionRead]:
    """
    Updates a Sub Question by its id

    Required roles:
    - admin
    - manager
    """
    current_question_sub = await crud.sub_question.get(id=sub_question_id)
    if not current_question_sub:
        raise IdNotFoundException(SubQuestion, sub_question_id)
    # if not is_authorized(current_user, "read", current_question_sub):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this Sub Question because you did not created it",
    #     )

    quiz_updated = await crud.sub_question.update(
        obj_new=sub_question, obj_current=current_question_sub
    )
    return create_response(data=quiz_updated)


@router.delete("/{sub_question_id}")
async def remove_sub_question(
    sub_question_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[SubQuestionRead]:
    """
    Deletes a Sub Question  by its id

    Required roles:
    - admin
    - manager
    """
    current_quiz = await crud.sub_question.get(id=sub_question_id)
    if not current_quiz:
        raise IdNotFoundException(SubQuestion, sub_question_id)
    quiz = await crud.sub_question.remove(id=sub_question_id)
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
