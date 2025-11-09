"""Post domain models"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    """Model for creating a post"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    category_id: int


class PostUpdate(BaseModel):
    """Model for updating a post"""
    title: str | None = Field(None, min_length=1, max_length=500)
    content: str | None = Field(None, min_length=1)


class Post(BaseModel):
    """Post domain model"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    category_id: int
    author_id: int
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class PostResponse(BaseModel):
    """Post response for MCP tools with additional metadata"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
    category_id: int
    category_name: str | None = None
    author_id: int
    author_username: str | None = None
    upvotes: int = 0
    downvotes: int = 0
    reply_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None
