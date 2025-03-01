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
from app.models.exam_paper_model import ExamPaper, ExamInstruction
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.exam_paper_schema import (
    ExamPaperCreate,
    ExamPaperRead,
    ExamPaperUpdate,
    InstructionCreate,
    InstructionRead,
    InstructionUpdate
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
async def get_exam_paper_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of ExamPapers
    """
    exams = await crud.exam_paper.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit
    )
    return create_response(data=exams)

@router.get("/get_exam_paper_properties")
async def get_exam_paper_properties(
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
    ):
    exam_headers= await crud.exam_paper.get_all_exam_properties(db_session=db_session)
    return exam_headers


@router.get("/get_by_created_at")
async def get_exams_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of ExamPapers ordered by created at datetime
    """
    exampapers = await crud.exam_paper.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=exampapers)


@router.get("/get_by_id/{exampaper_id}")
async def get_exam_paper_by_id(
    exampaper_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[ExamPaperRead]:
    """
    Gets a ExamPaper by its id
    """
    exampaper = await crud.exam_paper.get(id=exampaper_id)
    if not exampaper:
        raise IdNotFoundException(ExamPaper, exampaper_id)

    # print_hero.delay(hero.id)
    return create_response(data=exampaper)


@router.get("/get_by_slug/{exampaper_slug}")
async def get_exam_paper_by_slug(
    exampaper_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[ExamPaperRead]]:
    """
    Gets a ExamPaper by slug
    """
    exampaper = await crud.exam_paper.get_exam_paper_by_slug(slug=exampaper_slug)
    if not exampaper:
        raise NameNotFoundException(ExamPaper, exampaper_slug)

    return create_response(data=exampaper)


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
    exampaper: ExamPaperUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ExamPaperRead]:
    """
    Updates a ExamPaper by its id

    Required roles:
    - admin
    - manager
    """
    current_exam = await crud.exam_paper.get(id=exampaper_id)
    if not current_exam:
        raise IdNotFoundException(ExamPaper, exampaper_id)
    # if not is_authorized(current_user, "read", current_inst):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this institution because you did not created it",
    #     )

    exam_updated = await crud.exam_paper.update(
        obj_new=exampaper, obj_current=current_exam
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
@router.post("/{exampaper_id}/questions/{question_set_id}")
async def add_question_set_to_exam_paper(
    exampaper_id: UUID,
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ExamPaperRead]:
    """
    Add a QuestionSet to an ExamPaper by ids

    Required roles:
    - admin
    - manager
    """
    exam_paper = await crud.exam_paper.get(id=exampaper_id)
    question_set = await crud.question_set.get(id=question_set_id)
    if not exam_paper or not question_set:
        raise HTTPException(status_code=404, detail="ExamPaper or QuestionSet not found")

    # Check if association already exist
    _association = await crud.exam_paper.check_existing_association_with_question_set(
        exampaper=exam_paper, question_set=question_set
    )

    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"ExamPaper '{exampaper_id}' is already associated with QuestionSet '{question_set_id}'",
        )
    else:
        exam_paper.question_sets.append(question_set)
        exampaper_with_quizset = await crud.exam_paper.add_related(
            appended_parent_object=exam_paper
        )
        return create_response(data=exampaper_with_quizset)


# @router.post("/{institution_id}/logo")
# async def upload_institution_logo(
#     valid_institution: Institution = Depends(user_deps.is_valid_institution),
#     title: str | None = Body(None),
#     description: str | None = Body(None),
#     institution_logo: UploadFile = File(...),
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
#     minio_client: MinioClient = Depends(deps.minio_auth),
# ) -> IPostResponseBase[InstitutionRead]:
#     """
#     Uploads a institution official logo by id

#     Required roles:
#     - admin
#     - manager
#     """
#     try:
#         image_modified = modify_image(BytesIO(institution_logo.file.read()))
#         data_file = minio_client.put_object(
#             file_name=institution_logo.filename,
#             file_data=BytesIO(image_modified.file_data),
#             content_type=institution_logo.content_type,
#         )
#         media = IMediaCreate(
#             title=title, description=description, path=data_file.file_name
#         )
#         inst = await crud.institution.update_institution_logo(
#             institution=valid_institution,
#             image=media,
#             heigth=image_modified.height,
#             width=image_modified.width,
#             file_format=image_modified.file_format,
#         )
#         return create_response(data=inst)
#     except Exception as e:
#         print(e)
#         return Response("Internal server error", status_code=500)
