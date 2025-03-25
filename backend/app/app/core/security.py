from datetime import datetime, timedelta
from typing import Any

import jwt
import bcrypt
from app.core.config import settings
from cryptography.fernet import Fernet
fernet = Fernet(str.encode(settings.ENCRYPT_KEY))

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token
    """
    # print(f"Decoding token: {token}")
    try:
        # First, check if the token is properly formatted
        if not token or "." not in token:
            raise jwt.DecodeError("Invalid token format")

        # Make sure token has 3 segments
        segments = token.split('.')
        if len(segments) != 3:
            raise jwt.DecodeError("Not enough segments in token")

        # Decode the token
        decoded_token = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        # print("Decoded_token:", decoded_token)
        return decoded_token
    except jwt.ExpiredSignatureError:
        # Explicitly re-raise this so it can be caught appropriately
        raise
    except jwt.DecodeError as e:
        # Log details before re-raising
        print(f"Token decode error: {str(e)}, Token: {token[:10]}...")
        raise
    except Exception as e:
        # Catch any other exceptions and re-raise as DecodeError
        print(f"Unexpected decode error: {str(e)}")
        raise jwt.DecodeError(f"Token validation failed: {str(e)}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash using bcrypt"""
    # Convert strings to bytes if needed
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
        
    try:
        return bcrypt.checkpw(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    # Convert to bytes if it's a string
    if isinstance(password, str):
        password = password.encode('utf-8')
        
    # Generate a salt and hash the password
    salt = bcrypt.gensalt(rounds=12)  # 12 is a good default for security/performance
    hashed = bcrypt.hashpw(password, salt)
    
    # Return the hash as a string
    return hashed.decode('utf-8')


def get_data_encrypt(data) -> str:
    data = fernet.encrypt(data)
    return data.decode()


def get_content(variable: str) -> str:
    return fernet.decrypt(variable.encode()).decode()
