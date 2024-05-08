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
from app.models.module_model import Module
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.module_schema import (
    ModuleCreate,
    ModuleRead,
    ModuleUpdate,
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
async def get_course_module_list(
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ModuleRead]:
    """
    Gets a paginated list of course modules
    """
    modules = await crud.module.get_multi_paginated(params=params)
    return create_response(data=modules)


@router.get("/get_by_created_at")
async def get_module_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ModuleRead]:
    """
    Gets a paginated list of modules ordered by created at datetime
    """
    modules = await crud.module.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=modules)


@router.get("/get_by_id/{module_id}")
async def get_module_by_id(
    module_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[ModuleRead]:
    """
    Gets a course module by its id
    """
    module = await crud.module.get(id=module_id)
    if not module:
        raise IdNotFoundException(Module, module_id)

    # print_hero.delay(hero.id)
    return create_response(data=module)


@router.get("/get_by_slug/{module_slug}")
async def get_module_by_slug(
    module_slug: str,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[ModuleRead]]:
    """
    Gets a module by slug
    """
    module = await crud.module.get_module_by_slug(slug=module_slug)
    if not module:
        raise NameNotFoundException(Module, module_slug)

    return create_response(data=module)


@router.post("")
async def create_module(
    module: ModuleCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ModuleRead]:
    """
    Creates a new Course Module

    Required roles:
    - admin
    - manager
    """

    module = await crud.module.create(
        obj_in=module, created_by_id=current_user.id
    )
    return create_response(data=module)


@router.put("/{module_id}")
async def update_module(
    module_id: UUID,
    module: ModuleUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ModuleRead]:
    """
    Updates a module by its id

    Required roles:
    - admin
    - manager
    """
    current_module = await crud.module.get(id=module_id)
    if not current_module:
        raise IdNotFoundException(Module, module_id)
    # if not is_authorized(current_user, "read", current_module):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this module because you did not created it",
    #     )

    module_updated = await crud.module.update(
        obj_new=module, obj_current=current_module
    )
    return create_response(data=module_updated)


@router.delete("/{module_id}")
async def remove_course_module(
    module_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ModuleRead]:
    """
    Deletes a module by its id

    Required roles:
    - admin
    - manager
    """
    current_module = await crud.module.get(id=module_id)
    if not current_module:
        raise IdNotFoundException(Module, module_id)
    module = await crud.module.remove(id=module_id)
    return create_response(data=module)

 
# @router.post("/{programme_id}/image")
# async def upload_module_image(
#     valid_module: Module = Depends(user_deps.is_valid_programme),
#     title: str | None = Body(None),
#     description: str | None = Body(None),
#     programme_image: UploadFile = File(...),
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
#     minio_client: MinioClient = Depends(deps.minio_auth),
# ) -> IPostResponseBase[ProgrammeRead]:
#     """
#     Uploads a programme hero image by id

#     Required roles:
#     - admin
#     - manager
#     """
#     try:
#         image_modified = modify_image(BytesIO(programme_image.file.read()))
#         data_file = minio_client.put_object(
#             file_name=programme_image.filename,
#             file_data=BytesIO(image_modified.file_data),
#             content_type=programme_image.content_type,
#         )
#         media = IMediaCreate(
#             title=title, description=description, path=data_file.file_name
#         )
#         programme = await crud.programme.update_programme_image(
#             programme=valid_programme,
#             image=media,
#             heigth=image_modified.height,
#             width=image_modified.width,
#             file_format=image_modified.file_format,
#         )
#         return create_response(data=programme)
#     except Exception as e:
#         print(e)
#         return Response("Internal server error", status_code=500)



