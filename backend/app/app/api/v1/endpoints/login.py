from datetime import timedelta
from uuid import UUID

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
from app.schemas.auth_schema import LoginRequest, PasswordChange

router = APIRouter()


@router.post("",response_model=IPostResponseBase[Token])
async def login(
    login_data: LoginRequest,
    meta_data: IMetaGeneral = Depends(deps.get_general_meta),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[Token]:
    """
    Login for all users with provider support
    """
    if login_data.provider == AuthProvider.email:
        user = await crud.user.authenticate(email=login_data.email, password=login_data.password)
    else:
        user = await crud.user.get_by_email(email=login_data.email)
        if not user or user.provider != login_data.provider:
            raise HTTPException(
                status_code=400, 
                detail=f"No user found with this email for provider {login_data.provider}"
            )

    if not user:
        raise HTTPException(status_code=400, detail="Email or Password incorrect")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        await delete_tokens(redis_client, user, TokenType.ACCESS)
        await delete_tokens(redis_client, user, TokenType.REFRESH)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(user.id, expires_delta=refresh_token_expires)
    
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        try:
            access_token_added = await add_token_to_redis(
                redis_client,
                user,
                access_token,
                TokenType.ACCESS,
                int(access_token_expires.total_seconds()),
            )
            print(f"Access token added to Redis: {access_token_added}")
            
            refresh_token_added = await add_token_to_redis(
                redis_client,
                user,
                refresh_token,
                TokenType.REFRESH,
                int(refresh_token_expires.total_seconds()),
            )
            print(f"Refresh token added to Redis: {refresh_token_added}")
            
            access_tokens = await get_valid_tokens(redis_client, user.id, TokenType.ACCESS)
            print(f"Access tokens in Redis after login: {access_tokens}")
        except Exception as e:
            print(f"Error storing tokens in Redis: {str(e)}")

    data = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=user,
    )
    return create_response(meta=meta_data, data=data, message="Login correctly")


@router.post("/change_password",response_model=IPostResponseBase[Token])
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(deps.get_current_user()),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[Token]:
    """
    Change password
    """

    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid Current Password")

    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="New Password should be different that the current one",
        )

    new_hashed_password = get_password_hash(password_data.new_password)
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


@router.post("/new_access_token", response_model=IPostResponseBase[TokenRead])
async def get_new_access_token(
    body: RefreshToken = Body(...),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[TokenRead]:
    """
    Gets a new access token using the refresh token for future requests
    """
    try:
        print("Refresh token received:", body.refresh_token[:20] + "..." if body.refresh_token else "None")
        
        # Decode without verification to get the user_id
        unverified_payload = decode_token(body.refresh_token)
        user_id = unverified_payload["sub"]
        # print(f"Token payload: {unverified_payload}")
        
        # Check if token exists in Redis
        valid_refresh_tokens = await get_valid_tokens(
            redis_client, user_id, TokenType.REFRESH
        )
        
        if not valid_refresh_tokens or body.refresh_token not in valid_refresh_tokens:
            raise HTTPException(status_code=403, detail="Refresh token invalid or expired")

        # Now fully verify the token
        payload = decode_token(body.refresh_token)
        
        # Check token type - use get() to avoid KeyError
        token_type = payload.get("type")
        if token_type != "refresh" and "refresh" not in str(body.refresh_token).lower():
            print(f"Expected refresh token, got token type: {token_type}")
            raise HTTPException(status_code=403, detail="Invalid token type - not a refresh token")

        # Convert user_id string to UUID
        try:
            user_id_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        user = await crud.user.get(id=user_id_uuid)
        if not user or not user.is_active:
            raise HTTPException(status_code=404, detail="User inactive or not found")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user_id, expires_delta=access_token_expires
        )

        # Add new access token to Redis if enabled
        if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
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
    except Exception as e:
        print(f"Error in refresh token: {str(e)}")
        raise


@router.post("/access-token")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis_client: Redis = Depends(get_redis_client),
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests.
    This endpoint is used by Swagger UI for authorization.
    """
    # Authenticate the user
    user = await crud.user.authenticate(
        email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Delete existing tokens if Redis token blacklist is enabled
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        await delete_tokens(redis_client, user, TokenType.ACCESS)
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Store the token in Redis if token blacklist is enabled
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        try:
            token_added = await add_token_to_redis(
                redis_client,
                user,
                access_token,
                TokenType.ACCESS,
                int(access_token_expires.total_seconds()),
            )
            print(f"Access token added to Redis: {token_added}")
        except Exception as e:
            print(f"Error storing token in Redis: {str(e)}")
    
    # Return OAuth2 compatible response format for Swagger UI
    # Important: Do NOT use create_response() here as Swagger UI expects a specific format
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),  # Optional, can be helpful
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }
