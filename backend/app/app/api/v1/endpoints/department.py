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
from app.models.department_model import Department
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.department_schema import (
    DepartmentRead,
    DepartmentCreate,
    DepartmentUpdate,
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
async def get_department_list(
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[DepartmentRead]:
    """
    Gets a paginated list of departments
    """
    departments = await crud.department.get_multi_paginated(params=params)
    return create_response(data=departments)


@router.get("/get_by_created_at")
async def get_departments_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[DepartmentRead]:
    """
    Gets a paginated list of  departments ordered by created at datetime
    """
    departments = await crud.department.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=departments)


@router.get("/get_by_id/{department_id}")
async def get_department_by_id(
    department_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[DepartmentRead]:
    """
    Gets a deaprtment by its id
    """
    department = await crud.department.get(id=department_id)
    if not department:
        raise IdNotFoundException(Department, department_id)

    # print_hero.delay(hero.id)
    return create_response(data=department)


@router.get("/get_by_slug/{department_slug}")
async def get_department_by_slug(
    department_slug: str,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[DepartmentRead]]:
    """
    Gets a department by slug
    """
    department_frm_db = await crud.department.get_department_by_slug(
        slug=department_slug
    )
    if not department_frm_db:
        raise NameNotFoundException(Department, department_slug)

    return create_response(data=department_frm_db)


@router.post("")
async def create_department(
    department: DepartmentCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[DepartmentRead]:
    """
    Creates a new department

    Required roles:
    - admin
    - manager
    """

    _department = await crud.department.create(
        obj_in=department, created_by_id=current_user.id
    )
    return create_response(data=_department)


@router.put("/{department_id}")
async def update_department(
    department_id: UUID,
    department: DepartmentUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[DepartmentRead]:
    """
    Updates a department by its id

    Required roles:
    - admin
    - manager
    """
    current_dept = await crud.department.get(id=department_id)
    if not current_dept:
        raise IdNotFoundException(Department, department_id)
    if not is_authorized(current_user, "read", current_dept):
        raise HTTPException(
            status_code=403,
            detail="You are not Authorized to update this Department because you did not created it",
        )

    department_updated = await crud.department.update(
        obj_new=department, obj_current=current_dept
    )
    return create_response(data=department_updated)


@router.delete("/{department_id}")
async def remove_department(
    department_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[DepartmentRead]:
    """
    Deletes a department by its id

    Required roles:
    - admin
    - manager
    """
    current_depart = await crud.department.get(id=department_id)
    if not current_depart:
        raise IdNotFoundException(Department, department_id)
    department = await crud.department.remove(id=department_id)
    return create_response(data=department)


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


@router.post("/{department_id}/image")
async def upload_department_image(
    valid_department: Department= Depends(user_deps.is_valid_department),
    title: str | None = Body(None),
    description: str | None = Body(None),
    department_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[DepartmentRead]:
    """
    Uploads a department hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(department_image.file.read()))
        data_file = minio_client.put_object(
            file_name=department_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=department_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        department_photo = await crud.department.update_department_image(
            department=valid_department,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=department_photo)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)
