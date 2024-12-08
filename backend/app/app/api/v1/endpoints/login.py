from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import DecodeError, ExpiredSignatureError, MissingRequiredClaimError
from pydantic import EmailStr
from redis.asyncio import Redis

from app import crud
from app.api import deps
from app.api.deps import get_redis_client
from app.core import security
from app.core.config import settings
from app.core.security import decode_token, get_password_hash, verify_password
from app.models.user_model import User
from app.schemas.common_schema import AuthProvider, IMetaGeneral, TokenType
from app.schemas.response_schema import IPostResponseBase, create_response
from app.schemas.token_schema import RefreshToken, Token, TokenRead
from app.utils.token import add_token_to_redis, delete_tokens, get_valid_tokens

router = APIRouter()


@router.post("")
async def login(
    email: EmailStr = Body(...),
    password: str = Body(...),
    provider: AuthProvider = Body(default=AuthProvider.email),
    meta_data: IMetaGeneral = Depends(deps.get_general_meta),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[Token]:
    """
    Login for all users with provider support
    """
    if provider == AuthProvider.email:
        user = await crud.user.authenticate(email=email, password=password)
    else:
        user = await crud.user.get_by_email(email=email)
        if not user or user.provider != provider:
            raise HTTPException(
                status_code=400, 
                detail=f"No user found with this email for provider {provider}"
            )

    if not user:
        raise HTTPException(status_code=400, detail="Email or Password incorrect")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    print("Access Token:", {access_token})
    print("Access Token Expires:", {access_token_expires})
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    print("RefreshToken:",{refresh_token})
 
    # valid_access_tokens = await get_valid_tokens(
    #     redis_client, user.id, TokenType.ACCESS
    # )
    # print("valid_access_tokens:", {valid_access_tokens})
    # if valid_access_tokens:
    #     await add_token_to_redis(
    #         redis_client,
    #         user,
    #         access_token,
    #         TokenType.ACCESS,
    #         settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    #     )

        # valid_refresh_tokens = await get_valid_tokens(
        #     redis_client, user.id, TokenType.REFRESH
        # )
        # print("valid_refresh_tokens:", {valid_refresh_tokens})
        # if valid_refresh_tokens:
        # await add_token_to_redis(
        #     redis_client,
        #     user,
        #     refresh_token,
        #     TokenType.REFRESH,
        #     settings.REFRESH_TOKEN_EXPIRE_MINUTES,
        # )

    await add_token_to_redis(
        redis_client,
        user,
        access_token,
        TokenType.ACCESS,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    await add_token_to_redis(
        redis_client,
        user,
        refresh_token,
        TokenType.REFRESH,
        settings.REFRESH_TOKEN_EXPIRE_MINUTES,
    )
    data = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=user,
    )
    # print("data", data)
    # print("meta_data", meta_data)
    return create_response(meta=meta_data, data=data, message="Login correctly")


@router.post("/change_password")
async def change_password(
    current_password: str = Body(...),
    new_password: str = Body(...),
    current_user: User = Depends(deps.get_current_user()),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[Token]:
    """
    Change password
    """

    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid Current Password")

    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="New Password should be different that the current one",
        )

    new_hashed_password = get_password_hash(new_password)
    await crud.user.update(
        obj_current=current_user, obj_new={"hashed_password": new_hashed_password}
    )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        current_user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        current_user.id, expires_delta=refresh_token_expires
    )
    data = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=current_user,
    )

    await delete_tokens(redis_client, current_user, TokenType.ACCESS)
    await delete_tokens(redis_client, current_user, TokenType.REFRESH)
    await add_token_to_redis(
        redis_client,
        current_user,
        access_token,
        TokenType.ACCESS,
        settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    await add_token_to_redis(
        redis_client,
        current_user,
        refresh_token,
        TokenType.REFRESH,
        settings.REFRESH_TOKEN_EXPIRE_MINUTES,
    )

    return create_response(data=data, message="New password generated")


@router.post("/new_access_token", status_code=201)
async def get_new_access_token(
    body: RefreshToken = Body(...),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[TokenRead]:
    """
    Gets a new access token using the refresh token for future requests
    """
    print("Body.....................")
    # print(redis_client)
    # First check if the refresh token exists in Redis
    try:

        # Decode without verification to get the user_id
        unverified_payload = decode_token(body.refresh_token)
        user_id = unverified_payload["sub"]
        # print(user_id)
        # print(unverified_payload)
        valid_refresh_tokens = await get_valid_tokens(
            redis_client, user_id, TokenType.REFRESH
        )
        # print(valid_refresh_tokens)
        if not valid_refresh_tokens or body.refresh_token not in valid_refresh_tokens:
            raise HTTPException(status_code=403, detail="Refresh token invalid")

        # Now fully verify the token
        payload = decode_token(body.refresh_token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your token has expired. Please log in again.",
        )
    except (DecodeError, MissingRequiredClaimError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token format. Please log in again.",
        )

    if payload["type"] != "refresh":
        raise HTTPException(status_code=404, detail="Incorrect token type")

    user = await crud.user.get(id=user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=404, detail="User inactive or not found")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user_id, expires_delta=access_token_expires
    )

    valid_access_tokens = await get_valid_tokens(
        redis_client, user.id, TokenType.ACCESS
    )
    if valid_access_tokens:
        await add_token_to_redis(
            redis_client,
            user,
            access_token,
            TokenType.ACCESS,
            settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )

    return create_response(
        data=TokenRead(access_token=access_token, token_type="bearer"),
        message="Access token generated correctly",
    )


@router.post("/access-token")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis_client: Redis = Depends(get_redis_client),
) -> TokenRead:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await crud.user.authenticate(
        email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user. Contact your Admin")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    # print("Access Token Expires:", {access_token_expires})
    valid_access_tokens = await get_valid_tokens(
        redis_client, user.id, TokenType.ACCESS
    )
    if valid_access_tokens:
        await add_token_to_redis(
            redis_client,
            user,
            access_token,
            TokenType.ACCESS,
            settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        )
    return TokenRead(access_token=access_token, token_type="bearer")
