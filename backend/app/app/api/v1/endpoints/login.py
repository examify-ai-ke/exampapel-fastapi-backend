from datetime import timedelta
from uuid import UUID
import logging

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
    logging.debug(f"Login attempt with email: {login_data.email}, provider: {login_data.provider}")
    
    if login_data.provider == AuthProvider.email:
        logging.debug(f"Authenticating with email provider")
        user = await crud.user.authenticate(email=login_data.email, password=login_data.password)
    else:
        logging.debug(f"Authenticating with {login_data.provider} provider")
        user = await crud.user.get_by_email(email=login_data.email)
        if not user or user.provider != login_data.provider:
            logging.warning(f"No user found with email {login_data.email} for provider {login_data.provider}")
            raise HTTPException(
                status_code=400, 
                detail=f"No user found with this email for provider {login_data.provider}"
            )

    if not user:
        logging.warning(f"Authentication failed for email: {login_data.email}")
        raise HTTPException(status_code=400, detail="Email or Password incorrect")
    elif not user.is_active:
        logging.warning(f"Login attempt for inactive user: {login_data.email}")
        raise HTTPException(status_code=400, detail="User is inactive")

    logging.debug(f"User authenticated successfully: {user.id}")

    # Delete existing tokens - improved token management
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        logging.debug(f"Deleting existing tokens for user: {user.id}")
        # Get all keys for this user before creating new tokens
        await delete_tokens(redis_client, user, TokenType.ACCESS)
        await delete_tokens(redis_client, user, TokenType.REFRESH)

    # Create tokens
    logging.debug(f"Creating new access token for user: {user.id}")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(user.id, expires_delta=access_token_expires)
    
    logging.debug(f"Creating new refresh token for user: {user.id}")
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = security.create_refresh_token(user.id, expires_delta=refresh_token_expires)
    
    # Add tokens to Redis with proper key management
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        try:
            logging.debug(f"Storing tokens in Redis for user: {user.id}")
            # Store tokens using a consistent key pattern
            access_token_added = await add_token_to_redis(
                redis_client,
                user,
                access_token,
                TokenType.ACCESS,
                int(access_token_expires.total_seconds()),
            )
            
            refresh_token_added = await add_token_to_redis(
                redis_client,
                user,
                refresh_token,
                TokenType.REFRESH,
                int(refresh_token_expires.total_seconds()),
            )
            
            logging.debug(f"Tokens stored in Redis: access={access_token_added}, refresh={refresh_token_added}")
        except Exception as e:
            error_msg = f"Error storing tokens in Redis: {str(e)}"
            logging.error(error_msg)
            logging.exception("Exception details:")
            print(error_msg)

    logging.debug(f"Login successful for user: {user.id}")
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

    # Improved token handling
    # When password changes, invalidate all existing tokens
    await delete_tokens(redis_client, current_user, TokenType.ACCESS)
    await delete_tokens(redis_client, current_user, TokenType.REFRESH)
    
    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    
    access_token = security.create_access_token(
        current_user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(
        current_user.id, expires_delta=refresh_token_expires
    )
    
    # Store new tokens
    await add_token_to_redis(
        redis_client,
        current_user,
        access_token,
        TokenType.ACCESS,
        int(access_token_expires.total_seconds()),
    )
    await add_token_to_redis(
        redis_client,
        current_user,
        refresh_token,
        TokenType.REFRESH,
        int(refresh_token_expires.total_seconds()),
    )

    data = Token(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        user=current_user,
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
        logging.info(f"Processing refresh token request")
        
        # Decode without verification to get the user_id
        logging.info(f"Decoding refresh token without verification to extract user_id")
        unverified_payload = decode_token(body.refresh_token)
        user_id = unverified_payload["sub"]
        logging.info(f"Extracted user_id: {user_id}")
        
        # Check if token exists in Redis
        logging.info(f"Checking if refresh token exists in Redis for user {user_id}")
        valid_refresh_tokens = await get_valid_tokens(
            redis_client, user_id, TokenType.REFRESH
        )
        logging.info(f"Found {len(valid_refresh_tokens)} valid refresh tokens")
        
        if not valid_refresh_tokens or body.refresh_token not in valid_refresh_tokens:
            logging.warning(f"Refresh token not found in Redis or invalid for user {user_id}")
            raise HTTPException(status_code=403, detail="Refresh token invalid or expired")

        # Now fully verify the token
        logging.info(f"Fully verifying refresh token")
        payload = decode_token(body.refresh_token)
        logging.info(f"Token payload: {payload}")
        
        # Check token type - use get() to avoid KeyError
        token_type = payload.get("type")
        logging.info(f"Token type: {token_type}")
        if token_type != "refresh" and "refresh" not in str(body.refresh_token).lower():
            logging.warning(f"Invalid token type: {token_type}")
            raise HTTPException(status_code=403, detail="Invalid token type - not a refresh token")

        # Convert user_id string to UUID
        try:
            logging.info(f"Converting user_id string to UUID: {user_id}")
            user_id_uuid = UUID(user_id)
        except ValueError:
            logging.error(f"Invalid user ID format: {user_id}")
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        logging.info(f"Getting user from database")
        user = await crud.user.get(id=user_id_uuid)
        if not user or not user.is_active:
            logging.warning(f"User not found or inactive: {user_id}")
            raise HTTPException(status_code=404, detail="User inactive or not found")
        logging.info(f"Found user: {user.email}")

        # Generate new access token
        logging.info(f"Generating new access token for user {user_id}")
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            user_id, expires_delta=access_token_expires
        )
        logging.info(f"New access token generated")

        # Update Redis with the new access token - delete old ones first
        logging.info(f"Updating Redis with new access token")
        await delete_tokens(redis_client, user, TokenType.ACCESS)
        logging.info(f"Old access tokens deleted")
        
        token_added = await add_token_to_redis(
            redis_client,
            user,
            access_token,
            TokenType.ACCESS,
            int(access_token_expires.total_seconds()),
        )
        logging.info(f"New access token added to Redis: {token_added}")

        logging.info(f"Refresh token process completed successfully")
        return create_response(
            data=TokenRead(access_token=access_token, token_type="bearer"),
            message="Access token generated correctly",
        )
    except ExpiredSignatureError:
        logging.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except (DecodeError, MissingRequiredClaimError):
        logging.error("Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        error_msg = f"Error in refresh token: {str(e)}"
        logging.error(error_msg)
        logging.exception("Exception details:")
        print(error_msg)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/access-token")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    redis_client: Redis = Depends(get_redis_client),
) -> dict:
    """
    OAuth2 compatible token login, get an access token for future requests.
    This endpoint is used by Swagger UI for authorization.
    """
    logging.debug(f"OAuth2 login attempt with username: {form_data.username}")
    
    # Authenticate the user
    user = await crud.user.authenticate(
        email=form_data.username, password=form_data.password
    )
    
    if not user:
        logging.warning(f"OAuth2 authentication failed for email: {form_data.username}")
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        logging.warning(f"OAuth2 login attempt for inactive user: {form_data.username}")
        raise HTTPException(status_code=400, detail="Inactive user")

    logging.debug(f"OAuth2 user authenticated successfully: {user.id}")

    # Delete existing tokens to maintain token hygiene
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        logging.debug(f"Deleting existing access tokens for user: {user.id}")
        await delete_tokens(redis_client, user, TokenType.ACCESS)
    
    # Create access token
    logging.debug(f"Creating new access token for OAuth2 user: {user.id}")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Store the token in Redis with improved management
    if hasattr(settings, "USE_REDIS_TOKEN_BLACKLIST") and settings.USE_REDIS_TOKEN_BLACKLIST:
        try:
            logging.debug(f"Storing access token in Redis for OAuth2 user: {user.id}")
            token_added = await add_token_to_redis(
                redis_client,
                user,
                access_token,
                TokenType.ACCESS,
                int(access_token_expires.total_seconds()),
            )
            logging.debug(f"Token stored in Redis: {token_added}")
        except Exception as e:
            error_msg = f"Error storing token in Redis: {str(e)}"
            logging.error(error_msg)
            logging.exception("Exception details:")
            print(error_msg)
    
    logging.debug(f"OAuth2 login successful for user: {user.id}")
    
    # Return OAuth2 compatible response format for Swagger UI
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # seconds
    }
