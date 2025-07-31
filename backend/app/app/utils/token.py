from datetime import timedelta
from uuid import UUID
from redis.asyncio import Redis
from app.models.user_model import User
from app.schemas.common_schema import TokenType
import logging

# Add email verification token type
if 'email_verification' not in [t.value for t in TokenType]:
    # Add this only if it doesn't exist in the TokenType enum
    # You may need to update your TokenType enum instead
    EMAIL_VERIFICATION = "email_verification"
else:
    EMAIL_VERIFICATION = "email_verification"

async def add_token_to_redis(
    redis_client: Redis,
    user: User,
    token: str,
    token_type: TokenType,
    expiration_time: int,
) -> bool:
    """
    Add a token to Redis with better management.
    Stores each token type in its own key, so we can manage them separately.
    """
    try:
        logging.debug(f"Adding {token_type.value} token for user {user.id}")
        
        # Key format: user:{user_id}:tokens:{token_type}
        key = f"user:{user.id}:tokens:{token_type.value}"
        logging.debug(f"Using Redis key: {key}")
        
        # For better management:
        # 1. Get existing tokens (if any)
        # 2. Remove old tokens (optional, remove this if you want multiple valid tokens)
        # 3. Store the new token
        
        # Option 1: Allow only one token per type per user (logout all other sessions)
        # This replaces any existing token with the new one
        result = await redis_client.set(key, token, ex=expiration_time)
        logging.debug(f"Token stored in Redis with expiration of {expiration_time} seconds, result: {result}")
        
        # Verify token was stored properly
        stored_token = await redis_client.get(key)
        if stored_token:
            logging.debug(f"Verified token storage: Key {key} exists in Redis")
            ttl = await redis_client.ttl(key)
            logging.debug(f"Token TTL: {ttl} seconds")
        else:
            logging.warning(f"Failed to verify token storage: Key {key} not found after setting")
        
        return True
        
        # Option 2: Allow multiple sessions (commented out)
        # existing_tokens = await redis_client.smembers(key)
        # await redis_client.sadd(key, token)
        # await redis_client.expire(key, expiration_time)
        # return True
    except Exception as e:
        error_msg = f"Error in add_token_to_redis: {str(e)}"
        logging.error(error_msg)
        logging.exception("Exception details:")
        print(error_msg)  # Keep print for backward compatibility
        return False


async def get_valid_tokens(
    redis_client: Redis,
    user_id: UUID,
    token_type: TokenType,
) -> list[str]:
    """
    Get all valid tokens for a user of a specific type.
    Modified to work with the new key format.
    """
    try:
        print(f"Getting valid tokens for user {user_id} of type {token_type.value}")
        logging.debug(f"Getting valid tokens for user {user_id} of type {token_type.value}")
        key = f"user:{user_id}:tokens:{token_type.value}"
        logging.debug(f"Redis key: {key}")
        
        # Option 1: Single token per type
        token = await redis_client.get(key)
        logging.debug(f"Redis returned token: {token}")
        
        if not token:
            logging.debug(f"No token found for user {user_id} of type {token_type.value}")
            return []
            
        # Handle case where token might be bytes or string
        if isinstance(token, bytes):
            logging.debug(f"Converting token from bytes to string")
            token_str = token.decode("utf-8")
            logging.debug(f"Token after conversion: {token_str[:10]}...")
            return [token_str]
        else:
            logging.debug(f"Token is already a string: {token[:10]}...")
            return [token]  # Already a string
        
        # Option 2: Multiple tokens (commented out)
        # tokens = await redis_client.smembers(key)
        # logging.debug(f"Redis returned {len(tokens) if tokens else 0} tokens")
        # return [t.decode("utf-8") if isinstance(t, bytes) else t for t in tokens] if tokens else []
    except Exception as e:
        error_msg = f"Error in get_valid_tokens: {str(e)}"
        logging.error(error_msg)
        logging.exception("Exception details:")
        print(error_msg)  # Keep print for backward compatibility
        return []


async def delete_tokens(
    redis_client: Redis,
    user: User,
    token_type: TokenType,
) -> bool:
    """
    Delete all tokens of a specific type for a user.
    """
    try:
        key = f"user:{user.id}:tokens:{token_type.value}"
        await redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Error in delete_tokens: {str(e)}")
        return False

async def add_email_verification_token(
    redis_client: Redis,
    user_id: UUID,
    token: str,
    expiration_seconds: int = 86400  # 24 hours
) -> bool:
    """
    Store email verification token in Redis.
    Uses a separate key pattern from other tokens.
    """
    try:
        # Store token -> user_id mapping
        token_key = f"email_verification:{token}"
        await redis_client.set(token_key, str(user_id), ex=expiration_seconds)
        
        # Store user_id -> token mapping for easy invalidation
        user_key = f"user:{user_id}:email_verification"
        await redis_client.set(user_key, token, ex=expiration_seconds)
        return True
    except Exception as e:
        print(f"Error adding email verification token: {str(e)}")
        return False

async def verify_email_token(
    redis_client: Redis,
    token: str
) -> UUID | None:
    """
    Verify an email token and return the user ID if valid.
    Also deletes the token after verification to prevent reuse.
    """
    try:
        # Get user ID from token
        token_key = f"email_verification:{token}"
        user_id_bytes = await redis_client.get(token_key)
        
        if not user_id_bytes:
            return None
            
        user_id_str = user_id_bytes.decode('utf-8')
        user_id = UUID(user_id_str)
        
        # Delete token to prevent reuse
        await redis_client.delete(token_key)
        
        # Also delete user->token mapping
        user_key = f"user:{user_id}:email_verification"
        await redis_client.delete(user_key)
        
        return user_id
    except Exception as e:
        print(f"Error verifying email token: {str(e)}")
        return None

async def invalidate_email_verification_tokens(
    redis_client: Redis,
    user_id: UUID
) -> bool:
    """
    Invalidate all email verification tokens for a user
    """
    try:
        # Get current token for user
        user_key = f"user:{user_id}:email_verification"
        token_value = await redis_client.get(user_key) # Renamed from token_bytes for clarity

        if token_value:
            # Check if the value is bytes before decoding
            if isinstance(token_value, bytes):
                token = token_value.decode('utf-8')
            else:
                # Assume it's already a string if not bytes
                token = token_value

            # Delete token->user mapping
            token_key = f"email_verification:{token}"
            await redis_client.delete(token_key)

        # Delete user->token mapping regardless of whether a token was found
        await redis_client.delete(user_key)
        return True
    except Exception as e:
        # Log the error properly instead of just printing
        logging.error(f"Error invalidating email verification tokens for user {user_id}: {str(e)}")
        logging.exception("Exception details:")
        # Keep print for backward compatibility if needed, but logging is preferred
        print(f"Error invalidating email verification tokens: {str(e)}")
        return False
