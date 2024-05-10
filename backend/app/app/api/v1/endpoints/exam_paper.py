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


router = APIRouter()


@router.get("")
async def get_exam_paper_list(
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ExamPaperRead]: 
    """
    Gets a paginated list of ExamPapers
    """
    exams = await crud.exam_paper.get_multi_paginated(params=params)
    return create_response(data=exams)


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
    current_user: User = Depends(deps.get_current_user()),
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
    current_user: User = Depends(deps.get_current_user()),
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
    if len(instructions) != len(exampaper.instruction_ids):
        raise HTTPException(
            status_code=404, detail="Some instructions not found"
        )
    if len(modules) != len(exampaper.module_ids):
        raise HTTPException(status_code=404, detail="Some modules not found")

    # Add modules to the examPaper
    # exampaper..modules.extend(modules_list)  # Add the list of modules
    exampaper = await crud.exam_paper.create_with_related_list(
        obj_in=exampaper,related_list_object1=instructions,related_list_object2=modules,items1="instructions",items2="modules", created_by_id=current_user.id
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


# # Associate faculty with institution
# @router.post("/{institution_id}/faculties/{faculty_id}")
# async def add_faculty_to_institution(
#     institution_id: UUID,
#     faculty_id: UUID,
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
#     ) -> IDeleteResponseBase[InstitutionRead]:
#     """
#     Add a Faculty to an Institution by id

#     Required roles:
#     - admin
#     - manager
#     """
#     institution = await crud.institution.get(id=institution_id)
#     faculty = await crud.faculty.get(id=faculty_id)
#     if not institution or not faculty:
#         raise HTTPException(status_code=404, detail="Institution or Faculty not found")

#     # Check if association already exist
#     _association = await crud.institution.check_existing_association(
#         institution=institution, faculty=faculty
#     )

#     if _association is not None:
#         # If an association already exists, raise an error or return a suitable response
#         raise HTTPException(
#             status_code=400,
#             detail=f"Faculty '{faculty_id}' is already associated with Institution '{institution_id}'"
#         )
#     else:

#         institution.faculties.append(faculty)
#         institution_with_faculty = await crud.institution.add_related(
#             appended_parent_object=institution
#         )
#         return create_response(data=institution_with_faculty)


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
