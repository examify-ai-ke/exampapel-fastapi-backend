from app.utils.exceptions import (
    ContentNoChangeException,
    NameExistException,
    
)
from app.utils.exceptions.user_exceptions import RoleInUseException
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi_pagination import Params
from app import crud
from app.api import deps
from app.deps import role_deps
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.response_schema import (
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    IDeleteResponseBase,
    create_response,
)
from fastapi import Query
from app.schemas.common_schema import IOrderEnum
from app.schemas.role_schema import IRoleCreate, IRoleEnum, IRoleRead, IRoleUpdate
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()


@router.get("",response_model=IGetResponsePaginated[IRoleRead])
async def get_roles(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user(required_roles=[IRoleEnum.admin,IRoleEnum.manager])),
) -> IGetResponsePaginated[IRoleRead]:
    """
    Gets a paginated list of roles
    """
    roles = await crud.role.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        order=IOrderEnum.ascendent,
        order_by="name",
    )
    return create_response(data=roles)


@router.get("/{role_id}",response_model=IGetResponseBase[IRoleRead])
async def get_role_by_id(
    role: Role = Depends(role_deps.get_user_role_by_id),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[IRoleRead]:
    """
    Gets a role by its id
    """
    return create_response(data=role)


@router.post("", response_model=IPostResponseBase[IRoleRead])
async def create_role(
    role: IRoleCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPostResponseBase[IRoleRead]:
    """
    Create a new role

    Required roles:
    - admin
    """
    role_current = await crud.role.get_role_by_name(name=role.name)
    if role_current:
        raise NameExistException(Role, name=role_current.name)

    new_role = await crud.role.create(obj_in=role)
    return create_response(data=new_role)


@router.put("/{role_id}",response_model=IPutResponseBase[IRoleRead])
async def update_role(
    role: IRoleUpdate,
    current_role: Role = Depends(role_deps.get_user_role_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPutResponseBase[IRoleRead]:
    """
    Updates a role by its id

    Required roles:
    - admin
    """
    if current_role.name == role.name and current_role.description == role.description:
        raise ContentNoChangeException()

    exist_role = await crud.role.get_role_by_name(name=role.name)
    if exist_role:
        raise NameExistException(Role, name=role.name)

    updated_role = await crud.role.update(obj_current=current_role, obj_new=role)
    return create_response(data=updated_role)


@router.delete("/{role_id}", response_model=IDeleteResponseBase[IRoleRead])
async def delete_role(
    role: Role = Depends(role_deps.get_user_role_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[IRoleRead]:
    """
    Deletes a role by its id
    
    Required roles:
    - admin
    """
    # Check if role is in use by any users
    user_count = await crud.user.count_by_role(db_session=db_session, role_id=role.id)
    
    if user_count > 0:
        raise RoleInUseException(
            detail=f"Cannot delete role '{role.name}' as it is assigned to {user_count} users"
        )
    
    # Delete the role
    deleted_role = await crud.role.remove(id=role.id, db_session=db_session)
    
    return create_response(
        data=deleted_role,
        message=f"Role '{deleted_role.name}' successfully deleted"
    )
