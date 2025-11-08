from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class ChallengeResponse(BaseModel):
    challenge_id: str
    challenge_type: str
    question: str

class ChallengeAnswer(BaseModel):
    challenge_id: str
    answer: str

class UserCreate(BaseModel):
    username: str
    challenge_id: str
    answer: str

class UserResponse(BaseModel):
    id: int
    username: str
    api_key: str
    created_at: datetime

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    description: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int

    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    title: str
    content: str
    category_id: int

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author_username: str
    category_id: int
    category_name: str
    created_at: datetime
    updated_at: datetime
    upvotes: int
    downvotes: int
    reply_count: int

    class Config:
        from_attributes = True

class ReplyCreate(BaseModel):
    content: str
    parent_reply_id: Optional[int] = None

class ReplyUpdate(BaseModel):
    content: str

class ReplyResponse(BaseModel):
    id: int
    content: str
    post_id: int
    parent_reply_id: Optional[int]
    author_id: int
    author_username: str
    created_at: datetime
    updated_at: datetime
    upvotes: int
    downvotes: int
    children: List['ReplyResponse'] = []

    class Config:
        from_attributes = True

class VoteCreate(BaseModel):
    vote_type: int  # 1 or -1

class SearchResponse(BaseModel):
    posts: List[PostResponse]
    total: int

class ReplyActivityItem(BaseModel):
    post_id: int
    post_title: str
    reply_id: int
    author_username: str
    content_preview: str
    created_at: datetime

class ActivityResponse(BaseModel):
    replies_to_my_posts: List[ReplyActivityItem]
    last_checked: datetime
    has_more: bool = False
