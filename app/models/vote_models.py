"""Vote domain models"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class VoteCreate(BaseModel):
    """Model for creating a vote"""
    post_id: int | None = None
    reply_id: int | None = None
    vote_type: int = Field(..., description="1 for upvote, -1 for downvote")

    def model_post_init(self, __context):
        """Validate that exactly one of post_id or reply_id is set"""
        if self.post_id is None and self.reply_id is None:
            raise ValueError("Either post_id or reply_id must be provided")
        if self.post_id is not None and self.reply_id is not None:
            raise ValueError("Cannot vote on both post and reply simultaneously")
        if self.vote_type not in [1, -1]:
            raise ValueError("vote_type must be 1 (upvote) or -1 (downvote)")


class Vote(BaseModel):
    """Vote domain model"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    post_id: int | None = None
    reply_id: int | None = None
    vote_type: int
    created_at: datetime


class VoteResponse(BaseModel):
    """Vote response for MCP tools"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    post_id: int | None = None
    reply_id: int | None = None
    vote_type: int
    created_at: datetime
