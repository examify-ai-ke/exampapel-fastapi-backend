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
from app.models.exam_paper_model import ExamDescription
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.exam_paper_schema import (
    ExamDescriptionCreate,
    ExamDescriptionRead,
    ExamDescriptionUpdate,
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
async def get_exam_description_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamDescriptionRead]:
    """
    Gets a paginated list of exam descriptions
    """
    query = (
        select(ExamDescription)
        .options(
            selectinload(ExamDescription.created_by),  # Load creator details
        )
        .offset(skip)
        .limit(limit)
    )
    descriptions = await crud.exam_description.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=descriptions)


@router.get("/get_by_id/{exam_description_id}")
async def get_exam_description_by_id(
    exam_description_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[ExamDescriptionRead]:
    """
    Gets a Exam Description by its id
    """
    desc = await crud.exam_description.get(id=exam_description_id)
    if not desc:
        raise IdNotFoundException(ExamDescription, exam_description_id)

    return create_response(data=desc)


@router.post("")
async def create_exam_description(
    exam_description: ExamDescriptionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ExamDescriptionRead]:
    """
    Creates a new Exam Description

    Required roles:
    - admin
    - manager
    """

    description = await crud.exam_description.create(
        obj_in=exam_description, created_by_id=current_user.id
    )
    return create_response(data=description)


@router.put("/{exam_description_id}")
async def update_exam_description_paper(
    exam_description_id: UUID,
    examdescription: ExamDescriptionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ExamDescriptionRead]:
    """
    Updates a Exam Description by its id

    Required roles:
    - admin
    - manager
    """
    current_desc = await crud.exam_description.get(id=exam_description_id)
    if not current_desc:
        raise IdNotFoundException(ExamDescription, exam_description_id)
    # if not is_authorized(current_user, "read", current_inst):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this exam_title because you did not created it",
    #     )

    desc_updated = await crud.exam_title.update(
        obj_new=examdescription, obj_current=current_desc
    )
    return create_response(data=desc_updated)


@router.delete("/{exam_description_id}")
async def remove_exam_description(
    exam_description_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ExamDescriptionRead]:
    """
    Deletes a Exam Description by its id

    Required roles:
    - admin
    - manager
    """
    current_description = await crud.exam_description.get(id=exam_description_id)
    if not current_description:
        raise IdNotFoundException(ExamDescription, exam_description_id)
    description = await crud.exam_description.remove(id=exam_description_id)
    return create_response(data=description)


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
