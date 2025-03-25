from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Params
from app import crud
from app.api import deps
from app.deps import group_deps, user_deps
from app.models.group_model import Group
from app.models.user_model import User
from app.schemas.group_schema import (
    IGroupCreate,
    IGroupRead,
    IGroupReadWithUsers,
    IGroupUpdate,
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
from app.utils.exceptions import (
    IdNotFoundException,
    NameExistException,
)
from app.schemas.common_schema import IOrderEnum
from fastapi import Query
from sqlmodel.ext.asyncio.session import AsyncSession
# from app.schemas.delete_schema import IDeleteResponseBase

router = APIRouter()


@router.get("")
async def get_groups(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user(required_roles=[IRoleEnum.admin,IRoleEnum.manager])),
) -> IGetResponsePaginated[IGroupRead]:
    """
    Gets a paginated list of groups
    """
    groups = await crud.group.get_multi_paginated_ordered(
        db_session=db_session,
        skip=skip,
        limit=limit,
        order=IOrderEnum.ascendent,
        order_by="name",
    )
    return create_response(data=groups)


@router.get("/{group_id}")
async def get_group_by_id(
    group_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[IGroupReadWithUsers]:
    """
    Gets a group by its id
    """
    group = await crud.group.get(id=group_id)
    if group:
        return create_response(data=group)
    else:
        raise IdNotFoundException(Group, group_id)


@router.post("")
async def create_group(
    group: IGroupCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[IGroupRead]:
    """
    Creates a new group

    Required roles:
    - admin
    - manager
    """
    group_current = await crud.group.get_group_by_name(name=group.name)
    if group_current:
        raise NameExistException(Group, name=group.name)
    new_group = await crud.group.create(obj_in=group, created_by_id=current_user.id)
    return create_response(data=new_group)


@router.put("/{group_id}")
async def update_group(
    group: IGroupUpdate,
    current_group: Group = Depends(group_deps.get_group_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[IGroupRead]:
    """
    Updates a group by its id

    Required roles:
    - admin
    - manager
    """
    group_updated = await crud.group.update(obj_current=current_group, obj_new=group)
    return create_response(data=group_updated)


@router.post("/add_user/{user_id}/{group_id}")
async def add_user_into_a_group(
    user: User = Depends(user_deps.is_valid_user),
    group: Group = Depends(group_deps.get_group_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[IGroupRead]:
    """
    Adds a user into a group

    Required roles:
    - admin
    - manager
    """
    group = await crud.group.add_user_to_group(user=user, group_id=group.id)
    return create_response(message="User added to group", data=group)


@router.delete("/remove_user/{user_id}/{group_id}")
async def remove_user_from_group(
    user: User = Depends(user_deps.is_valid_user),
    group: Group = Depends(group_deps.get_group_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[IGroupRead]:
    """
    Removes a user from a group

    Required roles:
    - admin
    - manager
    """
    try:
        group = await crud.group.remove_user_from_group(user=user, group_id=group.id)
        return create_response(message="User removed from group", data=group)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to remove user from group: {str(e)}")


@router.delete("/{group_id}", response_model=IDeleteResponseBase[IGroupRead])
async def delete_group(
    group: Group = Depends(group_deps.get_group_by_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[IGroupRead]:
    """
    Deletes a group by its id if no users are attached to it
    
    Required roles:
    - admin
    - manager
    """
    # Check if users are attached to the group using the optimized method
    user_count = await crud.group.count_users_in_group(
        group_id=group.id, 
        db_session=db_session
    )
    
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete group '{group.name}' as it has {user_count} users attached. Remove all users first."
        )
    
    # Delete the group
    deleted_group = await crud.group.remove(id=group.id, db_session=db_session)
    
    return create_response(
        data=deleted_group,
        message=f"Group '{deleted_group.name}' successfully deleted"
    )
