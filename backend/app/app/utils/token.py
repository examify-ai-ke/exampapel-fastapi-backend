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
        key = f"{token_type}:{user.id}"
        print(f"Adding token to Redis - Key: {key}")  # Debug print
        
        # Add token to set
        result = await redis_client.sadd(key, token)
        print(f"SADD Result: {result}")  # Debug print
        
        # Set expiration
        exp_result = await redis_client.expire(key, expire_time * 60)
        print(f"EXPIRE Result: {exp_result}")  # Debug print
        
        # Verify token was stored
        stored_tokens = await redis_client.smembers(key)
        print(f"Stored tokens for {key}: {stored_tokens}")  # Debug print
        
    except Exception as e:
        print(f"Error storing token in Redis: {str(e)}")
        raise


# async def get_valid_tokens(redis_client: Redis, user_id: UUID, token_type: TokenType):
#     print("--------------------get_valid_tokens")
#     token_key = f"user:{user_id}:{token_type}"
#     print(token_key)
#     print(redis_client)
#     valid_tokens = await redis_client.smembers(token_key)
#     print(valid_tokens)
#     return valid_tokens


async def get_valid_tokens(
    redis_client: Redis, user_id: UUID, token_type: TokenType
) -> set[str]:
    """
    Retrieves valid tokens from Redis for a specific user and token type.
    """
    token_key = f"user:{user_id}:{token_type}"
    print(f"Fetching tokens from Redis with key: {token_key}")

    try:
        # Get the set of tokens for the given key
        valid_tokens = await redis_client.smembers(token_key)

        # Debugging output
        if sorted(valid_tokens):
            print(f"Valid tokens found for {token_key}: {valid_tokens}")
            return True
        else:
            # print(sorted(valid_tokens))
            print(f"No tokens found for {token_key}.")
            return False
    except Exception as e:
        print(f"Error fetching tokens from Redis for {token_key}: {e}")
        return False


async def delete_tokens(redis_client: Redis, user: User, token_type: TokenType):
    token_key = f"user:{user.id}:{token_type}"
    valid_tokens = await redis_client.smembers(token_key)
    if valid_tokens is not None:
        await redis_client.delete(token_key)
