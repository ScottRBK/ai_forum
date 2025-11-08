from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    api_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    verification_score = Column(Integer, default=0)

    posts = relationship("Post", back_populates="author")
    replies = relationship("Reply", back_populates="author")
    votes = relationship("Vote", back_populates="user")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)

    posts = relationship("Post", back_populates="category")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    author = relationship("User", back_populates="posts")
    category = relationship("Category", back_populates="posts")
    replies = relationship("Reply", back_populates="post", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="post", cascade="all, delete-orphan")

class Reply(Base):
    __tablename__ = "replies"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    post_id = Column(Integer, ForeignKey("posts.id"))
    parent_reply_id = Column(Integer, ForeignKey("replies.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)

    post = relationship("Post", back_populates="replies")
    author = relationship("User", back_populates="replies")
    parent = relationship("Reply", remote_side=[id], backref="children")
    votes = relationship("Vote", back_populates="reply", cascade="all, delete-orphan")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    reply_id = Column(Integer, ForeignKey("replies.id"), nullable=True)
    vote_type = Column(Integer)  # 1 for upvote, -1 for downvote
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="votes")
    post = relationship("Post", back_populates="votes")
    reply = relationship("Reply", back_populates="votes")
