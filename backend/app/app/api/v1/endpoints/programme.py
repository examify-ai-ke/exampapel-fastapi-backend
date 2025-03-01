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
from app.models.programme_model import Programme
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.programme_schema import (
    ProgrammeCreate,
    ProgrammeRead,
    ProgrammeUpdate,
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
async def get_programme_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ProgrammeRead]:
    """
    Gets a paginated list of programmes
    """
    programmes = await crud.programme.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit
    )
    return create_response(data=programmes)


@router.get("/get_by_created_at")
async def get_programme_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ProgrammeRead]:
    """
    Gets a paginated list of programmes ordered by created at datetime
    """
    programmes = await crud.programme.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=programmes)


@router.get("/get_by_id/{programme_id}")
async def get_programme_by_id(
    programme_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[ProgrammeRead]:
    """
    Gets a programme by its id
    """
    programme = await crud.programme.get(id=programme_id)
    if not programme:
        raise IdNotFoundException(Programme, programme_id)

    # print_hero.delay(hero.id)
    return create_response(data=programme)


@router.get("/get_by_slug/{programme_slug}")
async def get_programme_by_slug(
    programme_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[ProgrammeRead]]:
    """
    Gets a programme by slug
    """
    programme = await crud.programme.get_programme_by_slug(slug=programme_slug)
    if not programme:
        raise NameNotFoundException(Programme, programme_slug)

    return create_response(data=programme)


@router.post("")
async def create_programme(
    programme: ProgrammeCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ProgrammeRead]:
    """
    Creates a new programme

    Required roles:
    - admin
    - manager
    """

    programme = await crud.programme.create(
        obj_in=programme, created_by_id=current_user.id
    )
    return create_response(data=programme)


@router.put("/{programme_id}")
async def update_programme(
    programme_id: UUID,
    programme: ProgrammeUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ProgrammeRead]:
    """
    Updates a programme by its id

    Required roles:
    - admin
    - manager
    """
    current_programme = await crud.programme.get(id=programme_id)
    if not current_programme:
        raise IdNotFoundException(Programme, programme_id)
    # if not is_authorized(current_user, "read", current_programme):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this programme because you did not created it",
    #     )

    programme_updated = await crud.programme.update(
        obj_new=programme, obj_current=current_programme
    )
    return create_response(data=programme_updated)


@router.delete("/{programme_id}")
async def remove_programme(
    programme_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ProgrammeRead]:
    """
    Deletes a programme by its id

    Required roles:
    - admin
    - manager
    """
    current_programme = await crud.programme.get(id=programme_id)
    if not current_programme:
        raise IdNotFoundException(Programme, programme_id)
    programme = await crud.programme.remove(id=programme_id)
    return create_response(data=programme)


# # Associate faculty with institution
# @router.post("/institutions/{institution_id}/faculties/{faculty_id}")
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


@router.post("/{programme_id}/image")
async def upload_programme_image(
    valid_programme: Programme = Depends(user_deps.is_valid_programme),
    title: str | None = Body(None),
    description: str | None = Body(None),
    programme_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[ProgrammeRead]:
    """
    Uploads a programme hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(programme_image.file.read()))
        data_file = minio_client.put_object(
            file_name=programme_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=programme_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        programme = await crud.programme.update_programme_image(
            programme=valid_programme,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=programme)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


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
