import secrets
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from .database import SessionLocal # To create a db session
from .models.database import APIKey as APIKeyModel # The SQLAlchemy model
from sqlalchemy.sql import func # For func.now() if used for last_used_at

# Initialize CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_api_key(length: int = 32) -> str:
    """Generates a secure random API key."""
    return secrets.token_urlsafe(length)

def hash_api_key(api_key: str) -> str:
    """Hashes an API key using bcrypt."""
    return pwd_context.hash(api_key)

def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """Verifies a plain API key against a hashed version."""
    return pwd_context.verify(plain_api_key, hashed_api_key)

# API key header scheme
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_active_api_key(
    api_key_from_header: str = Depends(api_key_header_scheme),
    db: Session = Depends(get_db)
) -> APIKeyModel:
    if not api_key_from_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated: API key required"
        )

    # Query all active API keys.
    active_keys_in_db = db.query(APIKeyModel).filter(APIKeyModel.is_active == True).all()

    for db_key_obj in active_keys_in_db:
        if verify_api_key(api_key_from_header, db_key_obj.hashed_key):
            # Optionally, update last_used_at for the key here
            # db_key_obj.last_used_at = func.now()
            # db.commit()
            return db_key_obj # Return the key object

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API Key or key is not active"
    )
