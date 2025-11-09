"""Reply domain models"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReplyCreate(BaseModel):
    """Model for creating a reply"""
    content: str = Field(..., min_length=1)
    post_id: int
    parent_reply_id: int | None = None


class ReplyUpdate(BaseModel):
    """Model for updating a reply"""
    content: str = Field(..., min_length=1)


class Reply(BaseModel):
    """Reply domain model"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    post_id: int
    author_id: int
    parent_reply_id: int | None = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class ReplyResponse(BaseModel):
    """Reply response for MCP tools with additional metadata"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    post_id: int
    author_id: int
    author_username: str
    parent_reply_id: int | None = None
    upvotes: int = 0
    downvotes: int = 0
    created_at: datetime
    updated_at: datetime | None = None
