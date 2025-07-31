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
from app.models.campus_model import Campus
from app.models.user_model import User
from app.models.institution_model import Address
from app.schemas.common_schema import IOrderEnum
from app.schemas.campus_schema import (
    CampusRead,
    CampusCreate,
    CampusUpdate,
)
from app.schemas.address_schema import (
    AddressCreate,
    AddressUpdate,
    AddressRead,
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
from sqlmodel import select
from sqlalchemy.orm import selectinload
 
router = APIRouter()


@router.get("")
async def get_campus_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[CampusRead]:
    """
    Gets a paginated list of campus
    """
    query = (
        select(Campus)
        .options(
            selectinload(Campus.institution),
            selectinload(Campus.address),
            selectinload(Campus.created_by),
        )
    )
    campuses = await crud.campus.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=campuses)


@router.get("/get_by_created_at")
async def get_campus_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[CampusRead]:
    """
    Gets a paginated list of campuses ordered by created at datetime
    """
    campus = await crud.campus.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=campus)


@router.get("/get_by_id/{campus_id}")
async def get_campus_by_id(
    campus_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[CampusRead]:
    """
    Gets a campus by its id
    """
    campus = await crud.campus.get(
        id=campus_id,
        db_session=db_session,
        options=[
            selectinload(Campus.institution),
            selectinload(Campus.address),
            selectinload(Campus.created_by),
        ]
    )
    if not campus:
        raise IdNotFoundException(Campus, campus_id)

    # print_hero.delay(hero.id)
    return create_response(data=campus)


@router.get("/get_by_slug/{campus_slug}")
async def get_campus_by_slug(
    campus_slug: str,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[CampusRead]]:
    """
    Gets a Campus by slug
    """
    campus_frm_db = await crud.campus.get_campus_by_slug(slug=campus_slug)
    if not campus_frm_db:
        raise NameNotFoundException(Campus, campus_slug)

    return create_response(data=campus_frm_db)


@router.post("")
async def create_campus(
    campus: CampusCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[CampusRead]:
    """
    Creates a new Campus

    Required roles:
    - admin
    - manager
    """

    _campus = await crud.campus.create(obj_in=campus, created_by_id=current_user.id)
    return create_response(data=_campus)


@router.put("/{campus_id}")
async def update_campus(
    campus_id: UUID,
    campus: CampusUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[CampusRead]:
    """
    Updates a Campus by its id

    Required roles:
    - admin
    - manager
    """
    current_campus = await crud.campus.get(id=campus_id)
    if not current_campus:
        raise IdNotFoundException(Campus, campus_id)
    if not is_authorized(current_user, "read", current_campus):
        raise HTTPException(
            status_code=403,
            detail="You are not Authorized to update this Campus because you did not created it",
        )

    campus_updated = await crud.campus.update(
        obj_new=campus, obj_current=current_campus
    )
    return create_response(data=campus_updated)


@router.delete("/{campus_id}")
async def remove_campus(
    campus_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[CampusRead]:
    """
    Deletes a Campus by its id.
    Required roles:
    - admin
    - manager
    """
    current_campus = await crud.campus.get(id=campus_id)
    if not current_campus:
        raise IdNotFoundException(Campus, campus_id)
    campus = await crud.campus.remove(id=campus_id)
    return create_response(data=campus)



@router.post("/{campus_id}/image")
async def upload_campus_image(
    valid_campus: Campus= Depends(user_deps.is_valid_campus),
    title: str | None = Body(None),
    description: str | None = Body(None),
    campus_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[CampusRead]:
    """
    Uploads a campus hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(campus_image.file.read()))
        data_file = minio_client.put_object(
            file_name=campus_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=campus_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        campus_photo = await crud.campus.update_campus_image(
            campus=valid_campus,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=campus_photo)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


@router.post("/{campus_id}/address")
async def create_campus_address(
    campus_id: UUID,
    address: AddressCreate,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[CampusRead]:
    """
    Create an address for a campus

    Required roles:
    - admin
    - manager
    """
    # Verify campus exists
    campus = await crud.campus.get(
        id=campus_id, 
        db_session=db_session,
        options=[selectinload(Campus.address)]
    )
    if not campus:
        raise IdNotFoundException(Campus, campus_id)
    
    # Check if campus already has an address
    if campus.address:
        raise HTTPException(
            status_code=400,
            detail=f"Campus '{campus.name}' already has an address. Use PUT to update."
        )
    
    # Create a new address
    new_address = Address(**address.model_dump())
    new_address.campus_id = campus_id
    
    # Save address to database
    db_session.add(new_address)
    await db_session.commit()
    
    # Refresh campus to include the new address
    await db_session.refresh(campus)
    
    return create_response(data=campus)


@router.put("/{campus_id}/address")
async def update_campus_address(
    campus_id: UUID,
    address: AddressUpdate,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[CampusRead]:
    """
    Update an address for a campus

    Required roles:
    - admin
    - manager
    """
    # Verify campus exists
    campus = await crud.campus.get(
        id=campus_id, 
        db_session=db_session,
        options=[selectinload(Campus.address)]
    )
    if not campus:
        raise IdNotFoundException(Campus, campus_id)
    
    # Check if campus has an address
    if not campus.address:
        raise HTTPException(
            status_code=404,
            detail=f"Campus '{campus.name}' doesn't have an address. Create one first."
        )
    
    # Get address data excluding unset fields
    address_data = address.model_dump(exclude_unset=True)
    if not address_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )
    
    # Update existing address
    for key, value in address_data.items():
        setattr(campus.address, key, value)
    
    # Save updated address to database
    db_session.add(campus.address)
    await db_session.commit()
    
    # Refresh campus to include the updated address
    await db_session.refresh(campus)
    
    return create_response(data=campus)


@router.delete("/{campus_id}/address")
async def delete_campus_address(
    campus_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[CampusRead]:
    """
    Delete an address from a campus

    Required roles:
    - admin
    - manager
    """
    # Verify campus exists
    campus = await crud.campus.get(
        id=campus_id, 
        db_session=db_session,
        options=[selectinload(Campus.address)]
    )
    if not campus:
        raise IdNotFoundException(Campus, campus_id)
    
    # Check if campus has an address
    if not campus.address:
        raise HTTPException(
            status_code=404,
            detail=f"Campus '{campus.name}' doesn't have an address to delete."
        )
    
    # Get the address ID for deletion
    address_id = campus.address.id
    
    # Delete the address
    delete_query = select(Address).where(Address.id == address_id)
    result = await db_session.execute(delete_query)
    address_to_delete = result.scalar_one_or_none()
    
    if address_to_delete:
        await db_session.delete(address_to_delete)
        await db_session.commit()
    
    # Refresh campus to reflect the deletion
    await db_session.refresh(campus)
    
    return create_response(data=campus)
