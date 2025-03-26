from fastapi import HTTPException, BackgroundTasks, Depends, Query, Path
from io import BytesIO
from fastapi.responses import JSONResponse

from typing import Annotated
from uuid import UUID
from app.utils.exceptions import (
    IdNotFoundException,
    SelfFollowedException,
    UserFollowedException,
    UserNotFollowedException,
    UserSelfDeleteException,
)
from app import crud
from app.api import deps
from app.deps import user_deps
from app.models import User, UserFollow
from app.models.role_model import Role
from app.utils.minio_client import MinioClient
from app.utils.resize_image import modify_image
from app.core import security
from app.schemas.common_schema import AuthProvider
from fastapi import (
    APIRouter,
    Body,
    File,
    Response,
    UploadFile,
    status,
)
from app.schemas.media_schema import IMediaCreate
from app.schemas.response_schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    create_response,
)
from app.schemas.role_schema import IRoleEnum
from app.schemas.user_follow_schema import IUserFollowRead
from app.schemas.user_schema import (
    IUserCreate,
    IUserRead,
    IUserReadWithoutGroups,
    IUserStatus,
    IUserUpdate,
    BulkVerificationResponse,
    BulkVerificationUserInfo,
    UserVerificationStatus,
    EmailVerificationResult,
)
from app.schemas.token_schema import Token
from app.schemas.user_follow_schema import (
    IUserFollowReadCommon,
)
from fastapi_pagination import Params
from sqlmodel import and_, select, col, or_, text
from app.utils.social_auth import verify_social_token
from redis.asyncio import Redis
from datetime import timedelta
from app.core.config import settings
from app.core.security import create_email_verification_token, decode_token
from app.utils.email import send_verification_email
from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidTokenError
import logging
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Define the /me endpoint BEFORE any endpoints with UUID parameters
@router.get("/me", response_model=IGetResponseBase[IUserRead])
async def read_user_me(
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[IUserRead]:
    """
    Get current user.
    """
    return create_response(data=current_user)


@router.get("/list",response_model=IGetResponsePaginated[IUserReadWithoutGroups])
async def read_users_list(
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IGetResponsePaginated[IUserReadWithoutGroups]:
    """
    Retrieve users. Requires admin or manager role

    Required roles:
    - admin
    - manager
    """
    users = await crud.user.get_multi_paginated_ordered(skip=skip, limit=limit, order_by="created_at")
    return create_response(data=users)


@router.get("/list/by_role_name",response_model=IGetResponsePaginated[IUserReadWithoutGroups])
async def read_users_list_by_role_name(
    name: str = "",
    user_status: Annotated[
        IUserStatus,
        Query(
            title="User status",
            description="User status, It is optional. Default is active",
        ),
    ] = IUserStatus.active,
    role_name: str = "",
    params: Params = Depends(),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IGetResponsePaginated[IUserReadWithoutGroups]:
    """
    Retrieve users by role name and status. Requires admin role

    Required roles:
    - admin
    """
    user_status = True if user_status == IUserStatus.active else False
    query = (
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(
            and_(
                col(Role.name).ilike(f"%{role_name}%"),
                User.is_active == user_status,
                or_(
                    col(User.first_name).ilike(f"%{name}%"),
                    col(User.last_name).ilike(f"%{name}%"),
                    text(
                        f"""'{name}' % concat("User".last_name, ' ', "User".first_name)"""
                    ),
                    text(
                        f"""'{name}' % concat("User".first_name, ' ', "User".last_name)"""
                    ),
                ),
            )
        )
        .order_by(User.first_name)
    )
    users = await crud.user.get_multi_paginated(query=query, params=params)
    return create_response(data=users)


@router.get("/order_by_created_at",response_model=IGetResponsePaginated[IUserReadWithoutGroups])
async def get_user_list_order_by_created_at(
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IGetResponsePaginated[IUserReadWithoutGroups]:
    """
    Gets a paginated list of users ordered by created datetime

    Required roles:
    - admin
    - manager
    """
    users = await crud.user.get_multi_paginated_ordered(
        skip=skip, limit=limit, order_by="created_at"
    )
    return create_response(data=users)


@router.get("/following",response_model=IGetResponsePaginated[IUserFollowReadCommon])
async def get_following(
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[IUserFollowReadCommon]:
    """
    Lists the people who the authenticated user follows.
    """
    query = (
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.follower_count,
            User.following_count,
            UserFollow.is_mutual,
        )
        .join(UserFollow, User.id == UserFollow.target_user_id)
        .where(UserFollow.user_id == current_user.id)
    )
    users = await crud.user.get_multi_paginated_ordered(query=query, skip=skip, limit=limit)
    return create_response(data=users)


@router.get(
    "/following/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def check_is_followed_by_user_id(
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(deps.get_current_user()),
):
    """
    Check if a person is followed by the authenticated user
    """
    result = await crud.user_follow.get_follow_by_user_id_and_target_user_id(
        user_id=user.id, target_user_id=current_user.id
    )
    if not result:
        raise UserNotFollowedException(user_name=user.last_name)

    raise UserFollowedException(target_user_name=user.last_name)


@router.get("/followers",response_model=IGetResponsePaginated[IUserFollowReadCommon])
async def get_followers(
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[IUserFollowReadCommon]:
    """
    Lists the people following the authenticated user.
    """
    query = (
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.follower_count,
            User.following_count,
            UserFollow.is_mutual,
        )
        .join(UserFollow, User.id == UserFollow.user_id)
        .where(UserFollow.target_user_id == current_user.id)
    )
    users = await crud.user.get_multi_paginated_ordered(query=query, skip=skip, limit=limit)
    return create_response(data=users)


@router.get("/{user_id}/followers",response_model=IGetResponsePaginated[IUserFollowReadCommon])
async def get_user_followed_by_user_id(
    user_id: UUID = Depends(user_deps.is_valid_user_id),
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[IUserFollowReadCommon]:
    """
    Lists the people following the specified user.
    """
    query = (
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.follower_count,
            User.following_count,
            UserFollow.is_mutual,
        )
        .join(UserFollow, User.id == UserFollow.user_id)
        .where(UserFollow.target_user_id == user_id)
    )
    users = await crud.user.get_multi_paginated_ordered(query=query, skip=skip, limit=limit)
    return create_response(data=users)


@router.get("/{user_id}/following",response_model=IGetResponsePaginated[IUserFollowReadCommon])
async def get_user_following_by_user_id(
    user_id: UUID = Depends(user_deps.is_valid_user_id),
    # params: Params = Depends(),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[IUserFollowReadCommon]:
    """
    Lists the people who the specified user follows.
    """
    query = (
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.follower_count,
            User.following_count,
            UserFollow.is_mutual,
        )
        .join(UserFollow, User.id == UserFollow.target_user_id)
        .where(UserFollow.user_id == user_id)
    )
    users = await crud.user.get_multi_paginated_ordered(query=query, skip=skip, limit=limit)
    return create_response(data=users)


@router.get(
    "/{user_id}/following/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT
    
)
async def check_a_user_is_followed_another_user_by_id(
    user_id: UUID,
    target_user_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
):
    """
    Check if a user follows another user
    """
    if user_id == target_user_id:
        raise SelfFollowedException()

    user = await crud.user.get(id=user_id)
    if not user:
        raise IdNotFoundException(User, id=user_id)

    target_user = await crud.user.get(id=target_user_id)
    if not target_user:
        raise IdNotFoundException(User, id=target_user_id)

    result = await crud.user_follow.get_follow_by_user_id_and_target_user_id(
        user_id=user_id, target_user_id=target_user_id
    )
    if not result:
        raise UserNotFollowedException(
            user_name=user.last_name, target_user_name=target_user.last_name
        )


@router.put("/following/{target_user_id}",response_model=IPutResponseBase[IUserFollowRead])
async def follow_a_user_by_id(
    target_user_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IPutResponseBase[IUserFollowRead]:
    """
    Following a user
    """
    if target_user_id == current_user.id:
        raise SelfFollowedException()
    target_user = await crud.user.get(id=target_user_id)
    if not target_user:
        raise IdNotFoundException(User, id=target_user_id)

    current_follow_user = (
        await crud.user_follow.get_follow_by_user_id_and_target_user_id(
            user_id=current_user.id, target_user_id=target_user_id
        )
    )
    if current_follow_user:
        raise UserFollowedException(target_user_name=target_user.last_name)

    new_user_follow = await crud.user_follow.follow_a_user_by_target_user_id(
        user=current_user, target_user=target_user
    )
    return create_response(data=new_user_follow)


@router.delete("/following/{target_user_id}",response_model=IDeleteResponseBase[IUserFollowRead])
async def unfollowing_a_user_by_id(
    target_user_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IDeleteResponseBase[IUserFollowRead]:
    """
    Unfollowing a user
    """
    if target_user_id == current_user.id:
        raise SelfFollowedException()
    target_user = await crud.user.get(id=target_user_id)
    if not target_user:
        raise IdNotFoundException(User, id=target_user_id)

    current_follow_user = await crud.user_follow.get_follow_by_target_user_id(
        user_id=current_user.id, target_user_id=target_user_id
    )

    if not current_follow_user:
        raise UserNotFollowedException(user_name=target_user.last_name)

    user_follow = await crud.user_follow.unfollow_a_user_by_id(
        user_follow_id=current_follow_user.id,
        user=current_user,
        target_user=target_user,
    )
    return create_response(data=user_follow)


@router.get("/{user_id}",response_model=IGetResponseBase[IUserRead])
async def get_user_by_id(
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IGetResponseBase[IUserRead]:
    """
    Gets a user by his/her id

    Required roles:
    - admin
    - manager
    """
    # print(current_user)
    return create_response(data=user)


@router.delete("/{user_id}", response_model=IDeleteResponseBase[IUserRead])
async def remove_user(
    user_id: UUID = Depends(user_deps.is_valid_user_id),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IDeleteResponseBase[IUserRead]:
    """
    Deletes a user by his/her id

    Required roles:
    - admin
    """
    if current_user.id == user_id:
        raise UserSelfDeleteException()

    user = await crud.user.remove(id=user_id)
    return create_response(data=user, message="User removed")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IPostResponseBase[IUserRead])
async def create_user(
    new_user: IUserCreate = Depends(user_deps.user_exists),
    provider: AuthProvider = Body(default=AuthProvider.email),
    provider_user_id: str | None = Body(default=None),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPostResponseBase[IUserRead]:
    """
    Creates a new user with provider support
    """
    # Add provider information to new user
    new_user_dict = new_user.dict()
    new_user_dict.update({
        "provider": provider,
        "provider_user_id": provider_user_id,
        "email_verified": provider != AuthProvider.email # Auto-verify for social logins
    })
    
    user = await crud.user.create_with_role(obj_in=new_user_dict)
    return create_response(data=user)


@router.post("/request-verification", response_model=IPostResponseBase[bool])
async def request_email_verification(
    background_tasks: BackgroundTasks,
    current_user: IUserRead = Depends(deps.get_current_user()),
) -> IPostResponseBase[bool]:
    """
    Sends a verification email to the current user's email address
    """
    # Check if email is already verified
    if current_user.email_verified:
        return create_response(
            data=True,
            message="Email already verified"
        )
    
    # Get full user object to ensure we have the latest data
    user = await crud.user.get(id=current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create verification token (valid for 24 hours)
    token_expires = timedelta(hours=24)
    verification_token = create_email_verification_token(
        user.id, 
        expires_delta=token_expires
    )
    
    # Generate verification URL
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    
    # Send verification email as a background task
    background_tasks.add_task(
        send_verification_email,
        # email_to=user.email,
        email_to="david@techgrids.com",
        name=f"{user.first_name} {user.last_name}",
        verification_url=verification_url
    )
    
    return create_response(
        data=True,
        message="Verification email sent successfully"
    )


@router.post("/verify-email/{token}", response_model=IPostResponseBase[IUserRead])
async def verify_email(
    token: str,
) -> IPostResponseBase[IUserRead]:
    """
    Verify user email with verification token
    
    This endpoint should be called when a user clicks the verification
    link in their email. The token contains the user ID and is signed
    to prevent tampering.
    """
    try:
        # Decode and verify the token
        payload = decode_token(token)
        
        # Check token type
        if payload.get("type") != "email_verification":
            raise HTTPException(
                status_code=400,
                detail="Invalid verification token type"
            )
        
        # Extract user ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=400,
                detail="Invalid verification token"
            )
        
        # Convert to UUID
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid user ID in token"
            )

        # Get the user
        user = await crud.user.get(id=user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Check if already verified
        if user.email_verified:
            return create_response(
                data=user,
                message="Email already verified"
            )

        # Update user's email verification status
        updated_user = await crud.user.update(
            obj_current=user,
            obj_new={"email_verified": True}
        )

        return create_response(
            data=updated_user,
            message="Email verified successfully"
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=400,
            detail="Verification token has expired. Please request a new verification email."
        )
    except (DecodeError, InvalidTokenError):
        raise HTTPException(
            status_code=400,
            detail="Invalid verification token"
        )
    except Exception as e:
        logging.error(f"Email verification error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred during email verification"
        )


@router.post("/social-auth/{provider}",response_model=IPostResponseBase[Token])
async def social_auth(
    provider: AuthProvider,
    access_token: str = Body(...),
    redis_client: Redis = Depends(deps.get_redis_client),
) -> IPostResponseBase[Token]:
    """
    Handle social authentication
    """
    try:
        # Verify token with provider and get user info
        user_info = await verify_social_token(provider, access_token)

        # Check if user exists
        user = await crud.user.get_by_email(email=user_info["email"])

        if not user:
            # Get the default role
            default_role = await crud.role.get_role_by_name(name=settings.DEFAULT_ROLE_NAME)
            if not default_role:
                logging.error(f"Default role '{settings.DEFAULT_ROLE_NAME}' not found")
                raise HTTPException(
                    status_code=500,
                    detail="Error setting up user role"
                )

            # Create new user if doesn't exist
            new_user = {
                "email": user_info["email"],
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
                "provider": provider,
                "provider_user_id": user_info["sub"],
                "email_verified": True,
                "is_active": True,
                "role_id": default_role.id  # Use the fetched role ID
            }
            user = await crud.user.create_with_role(obj_in=new_user)

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=400,
                detail="Inactive user"
            )

        # Generate tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

        access_token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        refresh_token = security.create_refresh_token(
            user.id, expires_delta=refresh_token_expires
        )

        # Store refresh token in Redis
        await redis_client.set(
            f"refresh_token:{user.id}",
            refresh_token,
            ex=settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
        )

        # Create token response
        token_data = Token(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            user=user
        )

        return create_response(
            data=token_data,
            message=f"Successfully authenticated with {provider}"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error during social authentication: {str(e)}"
        )
    except Exception as e:
        logging.error(f"Social auth error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication"
        )


@router.post("/image",response_model=IPostResponseBase[IUserRead])
async def upload_my_image(
    title: str | None = Body(None),
    description: str | None = Body(None),
    image_file: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user()),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[IUserRead]:
    """
    Uploads a user image
    """
    try:
        image_modified = modify_image(BytesIO(image_file.file.read()))
        data_file = minio_client.put_object(
            file_name=image_file.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=image_file.content_type,
        )
        print("data_file", data_file)
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        user = await crud.user.update_photo(
            user=current_user,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=user)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


@router.post("/{user_id}/image",response_model=IPostResponseBase[IUserRead])
async def upload_user_image(
    user: User = Depends(user_deps.is_valid_user),
    title: str | None = Body(None),
    description: str | None = Body(None),
    image_file: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[IUserRead]:
    """
    Uploads a user image by his/her id

    Required roles:
    - admin
    """
    try:
        image_modified = modify_image(BytesIO(image_file.file.read()))
        data_file = minio_client.put_object(
            file_name=image_file.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=image_file.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        user = await crud.user.update_photo(
            user=user,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=user)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


@router.put("/{user_id}", response_model=IPutResponseBase[IUserRead])
async def update_user(
    user_update: IUserUpdate,
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[IUserRead]:
    """
    Updates a user by id
    
    Required roles:
    - admin
    - manager
    """
    updated_user = await crud.user.update(obj_current=user, obj_new=user_update)
    return create_response(data=updated_user)


@router.put("", response_model=IPutResponseBase[IUserRead])
async def update_my_user(
    user_update: IUserUpdate,
    current_user: User = Depends(deps.get_current_user()),
) -> IPutResponseBase[IUserRead]:
    """
    Updates the current user's profile
    
    This endpoint only allows users to update their own profile data.
    The user is identified by their authentication token, ensuring
    they can only modify their own information.
    """
    # Create a copy of the update data to modify safely
    update_data = user_update.dict(exclude_unset=True)
    
    # Security check: prevent users from updating restricted fields
    restricted_fields = ["is_superuser", "is_active", "role_id", "provider", "provider_user_id"]
    for field in restricted_fields:
        if field in update_data:
            update_data.pop(field)
    
    # Handle password update specially if included
    if "password" in update_data and update_data["password"]:
        # Hash the new password
        update_data["hashed_password"] = security.get_password_hash(update_data.pop("password"))
    
    # Check email uniqueness if changing email
    if "email" in update_data and update_data["email"] != current_user.email:
        existing_user = await crud.user.get_by_email(email=update_data["email"])
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
    
    # Update the user with the validated data
    updated_user = await crud.user.update(obj_current=current_user, obj_new=update_data)
    return create_response(data=updated_user)


@router.put("/{user_id}/activate", response_model=IPutResponseBase[IUserRead])
async def activate_user(
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPutResponseBase[IUserRead]:
    """
    Activates a user account
    
    Required roles:
    - admin
    """
    if user.is_active:
        return create_response(message="User is already active", data=user)
        
    updated_user = await crud.user.update(
        obj_current=user, 
        obj_new={"is_active": True}
    )
    return create_response(
        message=f"User {updated_user.email} has been activated",
        data=updated_user
    )


@router.put("/{user_id}/deactivate", response_model=IPutResponseBase[IUserRead])
async def deactivate_user(
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPutResponseBase[IUserRead]:
    """
    Deactivates a user account
    
    Required roles:
    - admin
    """
    # Prevent self-deactivation
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )
        
    # Prevent deactivating another admin
    if user.role and user.role.name == IRoleEnum.admin:
        raise HTTPException(
            status_code=403,
            detail="You cannot deactivate another admin's account"
        )
    
    if not user.is_active:
        return create_response(message="User is already inactive", data=user)
        
    updated_user = await crud.user.update(
        obj_current=user, 
        obj_new={"is_active": False}
    )
    return create_response(
        message=f"User {updated_user.email} has been deactivated",
        data=updated_user
    )


@router.post("/{user_id}/send-verification", response_model=IPostResponseBase[EmailVerificationResult])
async def admin_send_verification_email(
    background_tasks: BackgroundTasks,
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IPostResponseBase[EmailVerificationResult]:
    """
    Admin endpoint to send verification email to a specific user.
    
    This endpoint allows administrators to trigger a verification email
    for any user in the system. Useful for helping users who didn't
    receive their initial verification email or need a new one.
    
    Required roles:
    - admin
    """
    # Check if email is already verified
    if user.email_verified:
        result = EmailVerificationResult(
            success=True,
            email=user.email,
            user_id=str(user.id),
            already_verified=True,
            message=f"Email for user {user.email} is already verified"
        )
        return create_response(
            data=result,
            message=f"Email for user {user.email} is already verified"
        )
    
    # Create verification token (valid for 24 hours)
    token_expires = timedelta(hours=24)
    verification_token = create_email_verification_token(
        user.id, 
        expires_delta=token_expires
    )
    
    # Generate verification URL
    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    
    # Send verification email as a background task
    background_tasks.add_task(
        send_verification_email,
        email_to=user.email,
        name=f"{user.first_name} {user.last_name}",
        verification_url=verification_url
    )
    
    # Create and return response
    result = EmailVerificationResult(
        success=True,
        email=user.email,
        user_id=str(user.id),
        already_verified=False,
        message=f"Verification email has been sent to {user.email}"
    )
    
    return create_response(
        data=result,
        message=f"Verification email has been sent to {user.email}"
    )


@router.get("/{user_id}/verification-status", response_model=IGetResponseBase[UserVerificationStatus])
async def check_user_verification_status(
    user: User = Depends(user_deps.is_valid_user),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
) -> IGetResponseBase[UserVerificationStatus]:
    """
    Get a user's email verification status.
    
    This endpoint allows administrators to check whether a user's
    email has been verified.
    
    Required roles:
    - admin
    """
    verification_status = UserVerificationStatus(
        email=user.email,
        email_verified=user.email_verified,
        user_id=str(user.id),
        created_at=user.created_at
    )
    
    return create_response(
        data=verification_status,
        message="User verification status retrieved successfully"
    )


@router.post("/bulk/send-verification", response_model=IPostResponseBase[BulkVerificationResponse])
async def admin_bulk_send_verification_emails(
    background_tasks: BackgroundTasks,
    limit: int = Query(default=10, ge=1, le=100, description="Maximum number of emails to send"),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin])
    ),
    db_session: AsyncSession = Depends(deps.get_db)
) -> IPostResponseBase[BulkVerificationResponse]:
    """
    Admin endpoint to send verification emails to unverified users in bulk.
    
    This endpoint allows administrators to send verification emails to 
    multiple unverified users at once. The limit parameter controls
    how many emails will be sent in a single request to prevent
    overwhelming the email server.
    
    Required roles:
    - admin
    """
    # Query for unverified users
    query = select(User).where(User.email_verified == False).limit(limit)
    result = await db_session.execute(query)
    users = result.scalars().all()
    
    if not users:
        return create_response(
            data=BulkVerificationResponse(sent_count=0, users=[]),
            message="No unverified users found"
        )
    
    sent_count = 0
    user_list = []
    
    # Send verification emails to each user
    for user in users:
        # Create verification token (valid for 24 hours)
        token_expires = timedelta(hours=24)
        verification_token = create_email_verification_token(
            user.id, 
            expires_delta=token_expires
        )
        
        # Generate verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        
        # Send verification email as a background task
        background_tasks.add_task(
            send_verification_email,
            email_to=user.email,
            name=f"{user.first_name} {user.last_name}",
            verification_url=verification_url
        )
        
        sent_count += 1
        user_list.append(
            BulkVerificationUserInfo(
                id=str(user.id),
                email=user.email,
                name=f"{user.first_name} {user.last_name}"
            )
        )
    
    response_data = BulkVerificationResponse(
        sent_count=sent_count,
        users=user_list
    )
    
    return create_response(
        data=response_data,
        message=f"Verification emails sent to {sent_count} users"
    )
