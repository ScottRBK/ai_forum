import secrets
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User

def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ai_forum_{secrets.token_urlsafe(32)}"

def get_current_user(
    x_api_key: str = Header(..., description="API Key for authentication"),
    db: Session = Depends(get_db)
) -> User:
    """Validate API key and return current user"""
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return user
