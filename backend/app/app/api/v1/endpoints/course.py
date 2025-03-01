from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.programme_model import Programme
from app.schemas.programme_schema import ProgrammeCreate
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
from app.models.course_model import Course
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.course_schema import (
    CourseRead,
    CourseCreate,
    CourseUpdate,
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
async def get_course_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[CourseRead]:
    """
    Gets a paginated list of courses
    """
    courses = await crud.course.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit
    )
    return create_response(data=courses)


@router.get("/get_by_created_at")
async def get_course_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[CourseRead]:
    """
    Gets a paginated list of courses ordered by created at datetime
    """
    courses = await crud.course.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=courses)


@router.get("/get_by_id/{course_id}")
async def get_course_by_id(
    course_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[CourseRead]:
    """
    Gets a course by its id
    """
    course = await crud.course.get(id=course_id)
    if not course:
        raise IdNotFoundException(Course, course_id)

    # print_hero.delay(hero.id)
    return create_response(data=course)


@router.get("/get_by_slug/{course_slug}")
async def get_course_by_slug(
    course_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[CourseRead]]:
    """
    Gets a course by slug
    """
    course_frm_db = await crud.course.get_course_by_slug(slug=course_slug)
    if not course_frm_db:
        raise NameNotFoundException(Course, course_slug)

    return create_response(data=course_frm_db)


@router.post("")
async def create_course(
    course: CourseCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[CourseRead]:
    """
    Creates a new course

    Required roles:
    - admin
    - manager
    """

    _course = await crud.course.create(obj_in=course, created_by_id=current_user.id)
    return create_response(data=_course)


@router.put("/{course_id}")
async def update_course(
    course_id: UUID,
    course: CourseUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[CourseRead]:
    """
    Updates a course by its id

    Required roles:
    - admin
    - manager
    """
    current_course = await crud.course.get(id=course_id)
    if not current_course:
        raise IdNotFoundException(Course, course_id)
    # if not is_authorized(current_user, "read", current_course):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this Course because you did not created it",
    #     )

    course_updated = await crud.course.update(
        obj_new=course, obj_current=current_course
    )
    return create_response(data=course_updated)


@router.delete("/{course_id}")
async def remove_course(
    course_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[CourseRead]:
    """
    Deletes a course by its id

    Required roles:
    - admin
    - manager
    """
    current_course = await crud.course.get(id=course_id)
    if not current_course:
        raise IdNotFoundException(Course, course_id)
    course = await crud.course.remove(id=course_id)
    return create_response(data=course)


# @router.post("/logo")
# async def upload_institution_logo(
#     title: str | None = Body("Institution Logo"),
#     description: str | None = Body("The Institution official Logo"),
#     institution_logo: UploadFile = File(...),
#     current_user: User = Depends(deps.get_current_user()),
#     minio_client: MinioClient = Depends(deps.minio_auth),
# ) -> IPostResponseBase[InstitutionRead]:
#     """
#     Uploads a institution official logo/image
#     """
#     try:
#         image_modified = modify_image(BytesIO(institution_logo.file.read()))
#         data_file = minio_client.put_object(
#             file_name=institution_logo.filename,
#             file_data=BytesIO(image_modified.file_data),
#             content_type=institution_logo.content_type,
#         )
#         print("data_file", data_file)
#         media = IMediaCreate(
#             title=title, description=description, path=data_file.file_name
#         )
#         user = await crud.institution.update_institution_logo(
#             user=current_user,
#             institution_logo=media,
#             heigth=image_modified.height,
#             width=image_modified.width,
#             file_format=image_modified.file_format,
#         )
#         return create_response(data=user)
#     except Exception as e:
#         print(e)
#         return Response("Internal server error", status_code=500)


@router.post("/{course_id}/image")
async def upload_course_image(
    valid_course: Course = Depends(user_deps.is_valid_course),
    title: str | None = Body(None),
    description: str | None = Body(None),
    course_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[CourseRead]:
    """
    Uploads a course hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(course_image.file.read()))
        data_file = minio_client.put_object(
            file_name=course_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=course_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        course_photo = await crud.course.update_course_image(
            course=valid_course,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=course_photo)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


# Associate  Course with Module
@router.post("/{course_id}/modules/{module_id}")
async def add_module_to_course(
    course_id: UUID,
    module_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[CourseRead]:
    """
    Add a Module to a course by Ids

    Required roles:
    - admin
    - manager
    """
    course_db = await crud.course.get(id=course_id)
    module_db = await crud.module.get(id=module_id)
    if not course_db or not module_db:
        raise HTTPException(status_code=404, detail="Course or Module not found")

    # Check if association already exist
    _association = await crud.module.check_existing_association_with_course(
        course=course_db, module=module_db
    )

    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"Course '{course_db.name}' is already associated with Module '{module_db.name}'",
        )
    else:
        # Add the programme to the department's list of programmes
        course_db.modules.append(module_db)
        course_with_module = await crud.course.add_related(
            appended_parent_object=course_db
        )
        return create_response(data=course_with_module)
