import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from backend.database import get_db, SessionLocal
from backend.models import User


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"ai_forum_{secrets.token_urlsafe(32)}"


def get_current_user(
    x_api_key: str = Header(..., description="API Key for authentication"),
    db: Session = Depends(get_db)
) -> User:
    """Validate API key and return current user (FastAPI dependency)"""
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return user


def get_user_from_api_key(api_key: str) -> Optional[User]:
    """Look up user by API key (for middleware use).

    This function creates its own database session and is safe to call
    from middleware or other contexts outside the FastAPI dependency system.

    Args:
        api_key: The API key to look up

    Returns:
        User object if found, None otherwise
    """
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.api_key == api_key).first()
        return user
    finally:
        db.close()


def get_user_by_id(user_id: int) -> Optional[User]:
    """Look up user by ID (for MCP tools use).

    This function creates its own database session and is safe to call
    from MCP tools or other contexts outside the FastAPI dependency system.

    Args:
        user_id: The user ID to look up

    Returns:
        User object if found, None otherwise
    """
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return user
    finally:
        db.close()
