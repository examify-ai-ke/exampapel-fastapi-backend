from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app import crud
from app.api import deps
from app.models.comment_model import Comment
from app.models.user_model import User
from app.schemas.comment_schema import (
    CommentRead,
    CommentCreate,
    CommentUpdate,
    CommentReplyRead,
    CommentCountSchema
)
from app.schemas.common_schema import IOrderEnum
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
from app.utils.exceptions import IdNotFoundException

router = APIRouter()


@router.get("", response_model=IGetResponsePaginated[CommentRead])
async def get_comments_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[CommentRead]:
    """
    Gets a paginated list of Comments
    """
    comments = await crud.comment.get_multi_paginated_ordered(
        skip=skip, limit=limit, db_session=db_session
    )
    return create_response(data=comments)


@router.get("/by_answer/{answer_id}", response_model=IGetResponsePaginated[CommentRead])
async def get_comments_by_answer(
    answer_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    order_by: str = Query(default="created_at", description="Field to order by"),
    order: IOrderEnum = Query(default=IOrderEnum.descendent, description="Ascending or descending order"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[CommentRead]:
    """
    Gets a paginated list of Comments for a specific answer
    
    Parameters:
    - answer_id: UUID of the answer to get comments for
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - order_by: Field to order by, defaults to created_at
    - order: Order direction (ascendent or descendent)
    """
    comments = await crud.comment.get_comments_by_answer(
        answer_id=answer_id, 
        skip=skip, 
        limit=limit,
        order_by=order_by,
        order=order,
        db_session=db_session
    )
    return create_response(data=comments)


@router.get("/{comment_id}", response_model=IGetResponseBase[CommentRead])
async def get_comment_by_id(
    comment_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[CommentRead]:
    """
    Gets a comment by its id
    """
    comment = await crud.comment.get(id=comment_id, db_session=db_session)
    if not comment:
        raise IdNotFoundException(Comment, comment_id)
    return create_response(data=comment)


@router.post("", response_model=IPostResponseBase[CommentRead])
async def create_comment(
    comment: CommentCreate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[CommentRead]:
    """
    Creates a new Comment
    """
    new_comment = await crud.comment.create(
        obj_in=comment, created_by_id=current_user.id, db_session=db_session
    )
    return create_response(data=new_comment)


@router.post("/reply/{parent_id}", response_model=IPostResponseBase[CommentRead])
async def create_comment_reply(
    parent_id: UUID,
    comment: CommentCreate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[CommentRead]:
    """
    Creates a reply to an existing comment
    """
    # Ensure the parent comment exists
    parent_comment = await crud.comment.get(id=parent_id, db_session=db_session)
    if not parent_comment:
        raise IdNotFoundException(Comment, parent_id)
    
    # Set the parent_id for the reply
    comment_data = comment.model_dump()
    comment_data["parent_id"] = parent_id
    
    # Create the reply
    new_reply = await crud.comment.create(
        obj_in=CommentCreate(**comment_data),
        created_by_id=current_user.id,
        db_session=db_session
    )
    return create_response(data=new_reply)


@router.get("/reply/{parent_id}", response_model=IGetResponsePaginated[CommentRead])
async def get_comment_replies(
    parent_id: UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    order_by: str = Query(default="created_at", description="Field to order by"),
    order: IOrderEnum = Query(default=IOrderEnum.ascendent, description="Ascending or descending order"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[CommentRead]:
    """
    Gets a paginated list of replies for a specific comment
    """
    # Check if parent comment exists
    parent_comment = await crud.comment.get(id=parent_id, db_session=db_session)
    if not parent_comment:
        raise IdNotFoundException(Comment, parent_id)
        

    replies = await crud.comment.get_replies_by_parent(
        parent_id=parent_id,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order=order,
        db_session=db_session
    )
    return create_response(data=replies)


@router.put("/reply/{reply_id}", response_model=IPutResponseBase[CommentRead])
async def update_comment_reply(
    reply_id: UUID,
    comment: CommentUpdate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[CommentRead]:
    """
    Updates a reply by its id
    """
    current_reply = await crud.comment.get(id=reply_id, db_session=db_session)
    if not current_reply:
        raise IdNotFoundException(Comment, reply_id)
    
    # Ensure it is a reply
    if not current_reply.parent_id:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for updating replies only. Use PUT /comments/{id} for top-level comments.",
        )

    # Check authorization and time limit
    is_admin_or_manager = any(role.role_name in [IRoleEnum.admin, IRoleEnum.manager] for role in current_user.roles)

    if current_user.id != current_reply.created_by_id and not is_admin_or_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this reply",
        )
    
    if not is_admin_or_manager:
        # Check time limit (6 hours)
        time_diff = datetime.now(timezone.utc) - current_reply.created_at
        if time_diff.total_seconds() > 6 * 3600:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot update a reply after 6 hours",
            )
    
    comment_updated = await crud.comment.update(
        obj_current=current_reply, obj_new=comment, db_session=db_session
    )
    return create_response(data=comment_updated)


@router.delete("/reply/{reply_id}", response_model=IDeleteResponseBase[CommentRead])
async def delete_comment_reply(
    reply_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[CommentRead]:
    """
    Deletes a reply by its id
    """
    current_reply = await crud.comment.get(id=reply_id, db_session=db_session)
    if not current_reply:
         raise IdNotFoundException(Comment, reply_id)

    # Ensure it is a reply
    if not current_reply.parent_id:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is for deleting replies only. Use DELETE /comments/{id} for top-level comments.",
        )
    
    # Check authorization and time limit
    is_admin_or_manager = any(role.role_name in [IRoleEnum.admin, IRoleEnum.manager] for role in current_user.roles)

    if current_user.id != current_reply.created_by_id and not is_admin_or_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this reply",
        )
    
    if not is_admin_or_manager:
        # Check time limit (6 hours)
        time_diff = datetime.now(timezone.utc) - current_reply.created_at
        if time_diff.total_seconds() > 6 * 3600:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete a reply after 6 hours",
            )
    
    comment = await crud.comment.remove(id=reply_id, db_session=db_session)
    return create_response(data=comment)


@router.put("/{comment_id}", response_model=IPutResponseBase[CommentRead])
async def update_comment(
    comment_id: UUID,
    comment: CommentUpdate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[CommentRead]:
    """
    Updates a Comment by its id
    """
    current_comment = await crud.comment.get(id=comment_id, db_session=db_session)
    if not current_comment:
        raise IdNotFoundException(Comment, comment_id)
    
    # Check authorization and time limit
    is_admin_or_manager = any(role.role_name in [IRoleEnum.admin, IRoleEnum.manager] for role in current_user.roles)
    
    if current_user.id != current_comment.created_by_id and not is_admin_or_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this comment",
        )
    
    if not is_admin_or_manager:
        # Check time limit (6 hours)
        time_diff = datetime.now(timezone.utc) - current_comment.created_at
        if time_diff.total_seconds() > 6 * 3600:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot update a comment after 6 hours",
            )
    
    comment_updated = await crud.comment.update(
        obj_current=current_comment, obj_new=comment, db_session=db_session
    )
    return create_response(data=comment_updated)


@router.delete("/{comment_id}", response_model=IDeleteResponseBase[CommentRead])
async def delete_comment(
    comment_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[CommentRead]:
    """
    Deletes a Comment by its id
    """
    current_comment = await crud.comment.get(id=comment_id, db_session=db_session)
    if not current_comment:
        raise IdNotFoundException(Comment, comment_id)
    
    # Check authorization and time limit
    is_admin_or_manager = any(role.role_name in [IRoleEnum.admin, IRoleEnum.manager] for role in current_user.roles)

    if current_user.id != current_comment.created_by_id and not is_admin_or_manager:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to delete this comment",
        )
    
    if not is_admin_or_manager:
        # Check time limit (6 hours)
        time_diff = datetime.now(timezone.utc) - current_comment.created_at
        if time_diff.total_seconds() > 6 * 3600:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot delete a comment after 6 hours",
            )
    
    comment = await crud.comment.remove(id=comment_id, db_session=db_session)
    return create_response(data=comment)


@router.post("/{comment_id}/like", response_model=IPutResponseBase[CommentRead])
async def like_comment(
    comment_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[CommentRead]:
    """
    Likes a comment
    """
    comment = await crud.comment.get(id=comment_id, db_session=db_session)
    if not comment:
        raise IdNotFoundException(Comment, comment_id)
    
    # This would need to be implemented in the CRUD
    updated_comment = await crud.comment.like_comment(
        comment=comment, db_session=db_session
    )
    return create_response(data=updated_comment)


@router.post("/{comment_id}/dislike", response_model=IPutResponseBase[CommentRead])
async def dislike_comment(
    comment_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[CommentRead]:
    """
    Dislikes a comment
    """
    comment = await crud.comment.get(id=comment_id, db_session=db_session)
    if not comment:
        raise IdNotFoundException(Comment, comment_id)
    
    # This would need to be implemented in the CRUD
    updated_comment = await crud.comment.dislike_comment(
        comment=comment, db_session=db_session
    )
    return create_response(data=updated_comment)


@router.get("/count/{answer_id}", response_model=IGetResponseBase[CommentCountSchema])
async def get_comment_count_by_answer(
    answer_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[CommentCountSchema]:
    """
    Gets the total count of comments by answer
    
    Parameters:
    - answer_id: Optional UUID of an answer. If provided, returns count of comments for that answer.
    """
    print(f"Getting comment count for answer_id: {answer_id}")
    
    # Check if the answer exists (if answer_id is provided)
    if answer_id:
        answer = await crud.answer.get(id=answer_id, db_session=db_session)
        if not answer:
            print(f"Answer with id {answer_id} not found")
            return create_response(data=CommentCountSchema(count=0))
        print(f"Answer found: {answer.id}")
    
    count = await crud.comment.get_count_of_comments(answer_id=answer_id, db_session=db_session)
    return create_response(data=CommentCountSchema(count=count))
