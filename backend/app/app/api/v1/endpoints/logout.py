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
from app.schemas.common_schema import IMetaGeneral, TokenType
from app.schemas.response_schema import IPostResponseBase, create_response
from app.schemas.token_schema import RefreshToken, Token, TokenRead
from app.schemas.auth_schema import LogoutResponse
from app.utils.token import delete_tokens, get_valid_tokens
import logging

router = APIRouter()


# @router.post("")
@router.post("", response_model=IPostResponseBase[LogoutResponse])
async def logout(
    current_user: User = Depends(deps.get_current_user()),
    redis_client: Redis = Depends(get_redis_client),
) -> IPostResponseBase[LogoutResponse]:
    """
    Logout user by deleting their tokens from Redis
    Works for both traditional and social authentication
    """
    print(f"Logging out user {current_user.id}")
    success = True
    try:
        # Log the tokens being deleted (for debugging)
        access_tokens = await get_valid_tokens(redis_client, current_user.id, TokenType.ACCESS)
        refresh_tokens = await get_valid_tokens(redis_client, current_user.id, TokenType.REFRESH)
        
        print(f"Logging out user {current_user.id}: Found {len(access_tokens)} access tokens and {len(refresh_tokens)} refresh tokens")
        
        # Delete access tokens
        access_deleted = await delete_tokens(redis_client, current_user, TokenType.ACCESS)
        
        # Delete refresh tokens
        refresh_deleted = await delete_tokens(redis_client, current_user, TokenType.REFRESH)
        
        # For backward compatibility, also try old token format keys
        # This helps during transition to the new token management system
        legacy_keys = [
            f"user_tokens:{current_user.id}:*",
            f"user:{current_user.id}:*", 
            f"*:{current_user.id}:*"
        ]
        
        for pattern in legacy_keys:
            keys = await redis_client.keys(pattern)
            if keys:
                logging.info(f"Found {len(keys)} legacy keys for user {current_user.id}")
                await redis_client.delete(*keys)
        
        # If user is social auth, clean up provider-specific session data
        if hasattr(current_user, "provider") and current_user.provider != "email":
            provider_key = f"social_auth:{current_user.provider}:{current_user.id}"
            await redis_client.delete(provider_key)
        
        # Create a proper response using our schema
        logout_response = LogoutResponse(
            success=success,
            user_id=str(current_user.id),
            message="Logout successful" 
        )
        return create_response(data=logout_response)
    
    except Exception as e:
        logging.error(f"Error during logout for user {current_user.id}: {str(e)}")
        # We don't want to fail the logout even if there's an error with Redis
        # So we still return a success response, but log the error
        logout_response = LogoutResponse(
            success=True,  # Still return success to client
            user_id=str(current_user.id),
            message="Logout processed"
        )
        return create_response(data=logout_response)


