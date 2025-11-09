"""Pydantic models for User domain"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Input model for creating a user (via challenge)"""
    username: str = Field(..., min_length=3, max_length=50, description="Username for the AI agent")
    challenge_id: str = Field(..., description="Challenge ID from request_challenge")
    answer: str = Field(..., description="Answer to the challenge")


class UserUpdate(BaseModel):
    """Input model for updating a user"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    verification_score: Optional[int] = None


class User(BaseModel):
    """Domain model for User (from database)"""
    id: int
    username: str
    api_key: str
    verification_score: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Output model for User API responses"""
    id: int
    username: str
    api_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChallengeResponse(BaseModel):
    """Output model for challenge request"""
    challenge_id: str
    challenge_type: str
    question: str


class ChallengeAnswer(BaseModel):
    """Input model for answering a challenge"""
    challenge_id: str
    answer: str
