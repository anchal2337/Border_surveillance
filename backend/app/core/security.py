from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
import jwt
from passlib.context import CryptContext
from backend.app.core.config import settings

# Argon2 is the primary hasher (OWASP recommended), with pbkdf2 as backup
pwd_context = CryptContext(
    schemes=["argon2", "pbkdf2_sha256"],
    deprecated="auto"
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain text password against stored hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Computes secure hash for password."""
    return pwd_context.hash(password)

def create_access_token(
    subject: Union[str, Any], 
    role: Optional[str] = None, 
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generates signed JWT token for sentry operator session with embedded role."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if role:
        to_encode["role"] = str(role)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except (jwt.PyJWTError, Exception):
        return None
