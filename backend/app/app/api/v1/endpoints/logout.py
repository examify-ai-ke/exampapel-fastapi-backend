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
from app.utils.token import add_token_to_redis, delete_tokens, get_valid_tokens

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
    try:
        # Delete access tokens
        await delete_tokens(redis_client, current_user, TokenType.ACCESS)
        
        # Delete refresh tokens
        await delete_tokens(redis_client, current_user, TokenType.REFRESH)
        
        # If user is social auth, you might want to add additional cleanup
        if current_user.provider != "email":
            # Delete any provider-specific session data if needed
            provider_key = f"social_auth:{current_user.provider}:{current_user.id}"
            await redis_client.delete(provider_key)
        
        # Create a proper response using our schema
        logout_response = LogoutResponse()
        return create_response(data=logout_response)
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during logout: {str(e)}"
        )


