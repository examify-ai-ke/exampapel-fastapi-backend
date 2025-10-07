from collections.abc import AsyncGenerator
from typing import Callable, Optional
import logging
from uuid import UUID

from app.schemas.user_schema import IUserRead
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import DecodeError, ExpiredSignatureError, MissingRequiredClaimError
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app import crud
from app.core.config import settings
from app.core.security import decode_token
from app.db.session import SessionLocal, SessionLocalCelery
from app.models.user_model import User
from app.schemas.common_schema import IMetaGeneral, TokenType
from app.utils.minio_client import S3Client, MinioClient
from app.utils.token import get_valid_tokens

class DebugOAuth2PasswordBearer(OAuth2PasswordBearer):
    """OAuth2 password flow with more detailed error logging"""
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            # Log auth header for debugging
            auth_header = request.headers.get("Authorization")
            logging.debug(f"Auth header: {auth_header[:15]}..." if auth_header else "No auth header")
            
            # Get the token using the parent class
            token = await super().__call__(request)
            return token
        except HTTPException as e:
            # Log the authentication error
            logging.error(f"OAuth2 authentication failed: {str(e.detail)}")
            raise

# Use the debug version instead
oauth2_scheme = DebugOAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


async def get_redis_client() -> Redis:
    try:
        # Prepare connection arguments
        redis_args = {
            "db": settings.REDIS_DB,
            "max_connections": settings.REDIS_POOL_SIZE,
            "socket_timeout": settings.REDIS_POOL_TIMEOUT,
            "socket_connect_timeout": 2,
            "encoding": "utf8",
            "decode_responses": True,
        }
        
        # Check if REDIS_USE_PASSWORD setting exists, default to False
        use_password = getattr(settings, "REDIS_USE_PASSWORD", False)
        
        # Only add password if it's enabled and not empty
        if use_password and settings.REDIS_PASSWORD and settings.REDIS_PASSWORD.strip():
            redis_args["password"] = settings.REDIS_PASSWORD
            print(f"Using Redis with password authentication")
        else:
            print(f"Using Redis without password authentication")
        
        # Connect to Redis
        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        print(f"Connecting to Redis at {redis_url}, DB: {settings.REDIS_DB}")
        
        redis = await aioredis.from_url(redis_url, **redis_args)
        
        # Verify connection
        ping_result = await redis.ping()
        print(f"Redis ping result: {ping_result}")
        return redis
    except Exception as e:
        print(f"Failed to connect to Redis: {str(e)}")
        # Return a dummy object for testing without Redis
        if "AUTH" in str(e) and "without any password configured" in str(e):
            print("Redis has no password configured. Try updating REDIS_USE_PASSWORD=false in .env")
        raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_jobs_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocalCelery() as session:
        yield session


async def get_general_meta() -> IMetaGeneral:
    current_roles = await crud.role.get_multi(skip=0, limit=50)
    return IMetaGeneral(roles=current_roles)


def get_current_user(required_roles: list[str] = None) -> Callable[[], IUserRead]:
    async def current_user(
        access_token: str = Depends(oauth2_scheme),
        redis_client: Redis = Depends(get_redis_client),
    ) -> IUserRead:
        try:
            payload = decode_token(access_token)

            # Log the token payload for debugging
            # logging.debug(f"Token payload: {payload}")

            user_id_str  = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Could not validate credentials - missing user ID",
                )

            # Validate against Redis tokens if enabled
            try:
                if getattr(settings, "USE_REDIS_TOKEN_BLACKLIST", False):
                    valid_access_tokens = await get_valid_tokens(
                        redis_client, user_id_str, TokenType.ACCESS
                    )
                    if valid_access_tokens and access_token not in valid_access_tokens:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Token has been invalidated or logged out",
                        )
                    
                    # Extend session on activity
                    await extend_session_activity(redis_client, user_id_str, access_token)
                    
            except Exception as redis_error:
                # Log Redis errors but don't fail authentication if Redis check fails
                logging.error(f"Redis token validation error: {str(redis_error)}")

            # Get the user from database WITH relationships loaded

            # Get the user with relationships loaded
            user_id = UUID(user_id_str)
            user : User = await crud.user.get(
                id=user_id,
                options=[
                    selectinload(User.role),  # Load the role relationship
                    selectinload(User.groups) if hasattr(User, "groups") else None,
                    # Add any other relationships needed by the schema
                ],
            )

            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if not user.is_active:
                raise HTTPException(status_code=400, detail="Inactive user")

            # Check roles if required
            if required_roles:
                if not user.role:
                    raise HTTPException(
                        status_code=403, 
                        detail="User has no role assigned"
                    )

                is_valid_role = False
                for role in required_roles:
                    if role == user.role.name:
                        is_valid_role = True
                        break

                if not is_valid_role:
                    raise HTTPException(
                        status_code=403,
                        detail=f"""Role "{required_roles}" is required for this action""",
                    )

            return user

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your token has expired. Please log in again.",
            )
        except DecodeError as e:
            logging.error(f"Token decode error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format. Please log in again.",
            )
        except MissingRequiredClaimError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="There is no required field in your token.",
            )
        except Exception as e:
            logging.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication error: {str(e)}",
            )

    return current_user


async def extend_session_activity(redis_client: Redis, user_id: str, access_token: str) -> None:
    """
    Extend session timeout on user activity
    """
    try:
        access_key = f"user:{user_id}:tokens:access"
        if await redis_client.exists(access_key):
            # Extend the token expiration by the configured time
            await redis_client.expire(access_key, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
            logging.debug(f"Extended session for user {user_id}")
    except Exception as e:
        logging.error(f"Failed to extend session for user {user_id}: {str(e)}")


def minio_auth() -> S3Client:
    # minio_client = MinioClient(
    #     access_key=settings.MINIO_ROOT_USER,
    #     secret_key=settings.MINIO_ROOT_PASSWORD,
    #     bucket_name=settings.MINIO_BUCKET,
    #     minio_url=settings.MINIO_URL,
    #     secure=False,
    # )
    minio_client = S3Client(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        bucket_name=settings.S3_BUCKET_NAME,
    )
    return minio_client
