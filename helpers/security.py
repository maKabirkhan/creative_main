from passlib.context import CryptContext
from jose import jwt
import os
import uuid
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.helpers.db import get_user_by_email

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

security = HTTPBearer()

def create_persistent_token(email: str, user_id: int):
    """Generate a persistent JWT token with nonce for logout support."""
    # Generate a unique nonce for this token
    nonce = str(uuid.uuid4())
    token_data = {
        "sub": email, 
        "user_id": user_id,
        "nonce": nonce
    }
    return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password hash."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hash a plain password."""
    return pwd_context.hash(password)

expired_tokens = set()

def expire_token(token: str):
    """Mark a token as expired by adding its nonce to the blacklist"""
    try:
        # Decode token to get the nonce
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        nonce = payload.get("nonce")
        if nonce:
            expired_tokens.add(nonce)
            return True
    except JWTError:
        pass
    return False

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT and return current user from DB"""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        nonce: str = payload.get("nonce")
        
        if email is None or user_id is None:
            raise credentials_exception
            
        # Check if token is expired (nonce-based blacklisting)
        if nonce and nonce in expired_tokens:
            raise HTTPException(
                status_code=401,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"}
            )
            
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(email)
    if user is None or user["id"] != user_id:
        raise credentials_exception
    
    return user