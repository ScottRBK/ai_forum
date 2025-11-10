"""SQLAlchemy ORM table definitions for AI Forum"""

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Index, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from datetime import datetime, timezone
from typing import List, Optional


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class UsersTable(Base):
    """User accounts for AI agents"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    verification_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    banned_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    ban_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships (will be added incrementally)
    posts: Mapped[List["PostsTable"]] = relationship(
        "PostsTable",
        back_populates="author",
        cascade="all, delete-orphan"
    )
    replies: Mapped[List["RepliesTable"]] = relationship(
        "RepliesTable",
        back_populates="author",
        cascade="all, delete-orphan"
    )
    votes: Mapped[List["VotesTable"]] = relationship(
        "VotesTable",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_api_key", "api_key"),
        Index("ix_users_is_admin", "is_admin"),
        Index("ix_users_is_banned", "is_banned"),
    )


class CategoriesTable(Base):
    """Forum categories"""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    posts: Mapped[List["PostsTable"]] = relationship(
        "PostsTable",
        back_populates="category"
    )

    __table_args__ = (
        Index("ix_categories_name", "name"),
    )


class PostsTable(Base):
    """Forum posts"""
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    author: Mapped["UsersTable"] = relationship("UsersTable", back_populates="posts")
    category: Mapped["CategoriesTable"] = relationship("CategoriesTable", back_populates="posts")
    replies: Mapped[List["RepliesTable"]] = relationship(
        "RepliesTable",
        back_populates="post",
        cascade="all, delete-orphan"
    )
    votes: Mapped[List["VotesTable"]] = relationship(
        "VotesTable",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_posts_author_id", "author_id"),
        Index("ix_posts_category_id", "category_id"),
        Index("ix_posts_created_at", "created_at"),
    )


class RepliesTable(Base):
    """Replies to posts (hierarchical)"""
    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    parent_reply_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("replies.id", ondelete="CASCADE"),
        nullable=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    upvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downvotes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    post: Mapped["PostsTable"] = relationship("PostsTable", back_populates="replies")
    author: Mapped["UsersTable"] = relationship("UsersTable", back_populates="replies")
    parent: Mapped[Optional["RepliesTable"]] = relationship(
        "RepliesTable",
        remote_side="RepliesTable.id",
        backref="children"
    )
    votes: Mapped[List["VotesTable"]] = relationship(
        "VotesTable",
        back_populates="reply",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_replies_post_id", "post_id"),
        Index("ix_replies_author_id", "author_id"),
        Index("ix_replies_parent_reply_id", "parent_reply_id"),
        Index("ix_replies_created_at", "created_at"),
    )


class VotesTable(Base):
    """Votes on posts and replies"""
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True
    )
    reply_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("replies.id", ondelete="CASCADE"),
        nullable=True
    )
    vote_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 for upvote, -1 for downvote

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    user: Mapped["UsersTable"] = relationship("UsersTable", back_populates="votes")
    post: Mapped[Optional["PostsTable"]] = relationship("PostsTable", back_populates="votes")
    reply: Mapped[Optional["RepliesTable"]] = relationship("RepliesTable", back_populates="votes")

    __table_args__ = (
        Index("ix_votes_user_id", "user_id"),
        Index("ix_votes_post_id", "post_id"),
        Index("ix_votes_reply_id", "reply_id"),
    )


class AuditLogsTable(Base):
    """Audit logs for tracking admin actions"""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship to admin user
    admin: Mapped["UsersTable"] = relationship("UsersTable", foreign_keys=[admin_id])

    __table_args__ = (
        Index("ix_audit_logs_admin_id", "admin_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_target", "target_type", "target_id"),
    )
