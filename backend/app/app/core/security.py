from datetime import datetime, timedelta
from typing import Any
import uuid

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

fernet = Fernet(str.encode(settings.ENCRYPT_KEY))

JWT_ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access",
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
        "iss": "your-application-name",
        "aud": "your-frontend-url"
    }

    return jwt.encode(
        payload=to_encode,
        key=settings.ENCRYPT_KEY,
        algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(subject: str | Any, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }

    return jwt.encode(
        payload=to_encode,
        key=settings.ENCRYPT_KEY,
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    # First decode without verification to check token type
    unverified_payload = jwt.decode(token, options={"verify_signature": False})
    token_type = unverified_payload.get("type")

    # Set options based on token type
    options = {
        'verify_signature': True,
        'verify_exp': True,
        'verify_iat': True,
        'require': ['exp', 'iat', 'sub']
    }
    
    # Only verify audience for access tokens
    if token_type == "access":
        options['verify_aud'] = True
        return jwt.decode(
            jwt=token,
            key=settings.ENCRYPT_KEY,
            algorithms=[JWT_ALGORITHM],
            options=options,
            audience="your-frontend-url"
        )
    else:
        # For refresh tokens, don't verify audience
        return jwt.decode(
            jwt=token,
            key=settings.ENCRYPT_KEY,
            algorithms=[JWT_ALGORITHM],
            options=options
        )


def verify_password(plain_password: str | bytes, hashed_password: str | bytes) -> bool:
    if isinstance(plain_password, str):
        plain_password = plain_password.encode()
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode()

    return bcrypt.checkpw(plain_password, hashed_password)


def get_password_hash(plain_password: str | bytes) -> str:
    if isinstance(plain_password, str):
        plain_password = plain_password.encode()

    return bcrypt.hashpw(plain_password, bcrypt.gensalt()).decode()


def get_data_encrypt(data) -> str:
    data = fernet.encrypt(data)
    return data.decode()


def get_content(variable: str) -> str:
    return fernet.decrypt(variable.encode()).decode()
