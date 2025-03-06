from datetime import timedelta
from uuid import UUID
from redis.asyncio import Redis
from app.models.user_model import User
from app.schemas.common_schema import TokenType
import logging


async def add_token_to_redis(
    redis_client: Redis,
    user: User,
    token: str,
    token_type: TokenType,
    expire_time: int | None = None,
):
    """Add a token to Redis"""
    try:
        # Use consistent key format
        key = f"user:{user.id}:{token_type}"
        # print(f"Adding token to Redis - Key: {key}")  # Debug print

        # Add token to set
        result = await redis_client.sadd(key, token)
        # print(f"SADD Result: {result}")  # Debug print

        # Set expiration if provided
        if expire_time is not None:
            exp_result = await redis_client.expire(key, expire_time)
            # print(f"EXPIRE Result: {exp_result}")  # Debug print

        # Verify token was stored
        stored_tokens = await redis_client.smembers(key)
        # print(f"Stored tokens for {key}: {stored_tokens}")  # Debug print

        return result > 0
    except Exception as e:
        # print(f"Error storing token in Redis: {str(e)}")
        raise


async def get_valid_tokens(
    redis_client: Redis, user_id: UUID, token_type: TokenType
) -> set[str]:
    """
    Retrieves valid tokens from Redis for a specific user and token type.
    """
    token_key = f"user:{user_id}:{token_type}"
    # print(f"Fetching tokens from Redis with key: {token_key}")

    try:
        # Get the set of tokens for the given key
        valid_tokens = await redis_client.smembers(token_key)

        # Debugging output
        # print(f"Valid tokens found for {token_key}: {sorted(valid_tokens)}")
        return valid_tokens
    except Exception as e:
        # print(f"Error fetching tokens from Redis for {token_key}: {e}")
        return set()


async def delete_tokens(redis_client: Redis, user: User, token_type: TokenType):
    token_key = f"user:{user.id}:{token_type}"
    valid_tokens = await redis_client.smembers(token_key)
    if valid_tokens is not None:
        await redis_client.delete(token_key)
