"""Post repository for database operations"""

import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from app.models.post_models import Post, PostCreate, PostUpdate
from app.models.user_models import User
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import PostsTable, UsersTable, CategoriesTable, RepliesTable
from app.exceptions import NotFoundError, AuthenticationError

logger = logging.getLogger(__name__)


class PostgresPostRepository:
    """Repository for post database operations"""

    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def create_post(
        self,
        user_id: int,
        post_data: PostCreate
    ) -> Post:
        """
        Create a new post.

        Args:
            user_id: ID of the user creating the post
            post_data: Post creation data

        Returns:
            Created Post domain model
        """
        async with self.db_adapter.session() as session:
            post = PostsTable(
                title=post_data.title,
                content=post_data.content,
                category_id=post_data.category_id,
                author_id=user_id
            )

            session.add(post)
            await session.flush()
            await session.refresh(post)

            logger.info(
                "Created post",
                extra={
                    "post_id": post.id,
                    "author_id": user_id,
                    "category_id": post_data.category_id
                }
            )

            return Post.model_validate(post)

    async def get_posts(
        self,
        category_id: int | None = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[tuple[Post, str, str, int]]:
        """
        Get posts with pagination and optional category filter.

        Args:
            category_id: Optional category filter
            skip: Number of posts to skip (for pagination)
            limit: Maximum number of posts to return

        Returns:
            List of tuples: (Post, author_username, category_name, reply_count)
        """
        async with self.db_adapter.session() as session:
            # Build query with joins
            query = (
                select(
                    PostsTable,
                    UsersTable.username,
                    CategoriesTable.name,
                    func.count(RepliesTable.id).label('reply_count')
                )
                .join(UsersTable, PostsTable.author_id == UsersTable.id)
                .join(CategoriesTable, PostsTable.category_id == CategoriesTable.id)
                .outerjoin(RepliesTable, PostsTable.id == RepliesTable.post_id)
                .group_by(PostsTable.id, UsersTable.username, CategoriesTable.name)
                .order_by(PostsTable.created_at.desc())
            )

            # Apply category filter if provided
            if category_id is not None:
                query = query.where(PostsTable.category_id == category_id)

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await session.execute(query)
            rows = result.all()

            logger.info(
                "Retrieved posts",
                extra={
                    "count": len(rows),
                    "category_id": category_id,
                    "skip": skip,
                    "limit": limit
                }
            )

            return [
                (
                    Post.model_validate(row[0]),
                    row[1],  # author_username
                    row[2],  # category_name
                    row[3]   # reply_count
                )
                for row in rows
            ]

    async def get_post_by_id(self, post_id: int) -> tuple[Post, str, str, int] | None:
        """
        Get a single post by ID with metadata.

        Args:
            post_id: Post ID to retrieve

        Returns:
            Tuple of (Post, author_username, category_name, reply_count) or None
        """
        async with self.db_adapter.session() as session:
            query = (
                select(
                    PostsTable,
                    UsersTable.username,
                    CategoriesTable.name,
                    func.count(RepliesTable.id).label('reply_count')
                )
                .join(UsersTable, PostsTable.author_id == UsersTable.id)
                .join(CategoriesTable, PostsTable.category_id == CategoriesTable.id)
                .outerjoin(RepliesTable, PostsTable.id == RepliesTable.post_id)
                .where(PostsTable.id == post_id)
                .group_by(PostsTable.id, UsersTable.username, CategoriesTable.name)
            )

            result = await session.execute(query)
            row = result.first()

            if row:
                logger.info(
                    "Retrieved post",
                    extra={"post_id": post_id}
                )
                return (
                    Post.model_validate(row[0]),
                    row[1],  # author_username
                    row[2],  # category_name
                    row[3]   # reply_count
                )

            logger.warning(
                "Post not found",
                extra={"post_id": post_id}
            )
            return None

    async def update_post(
        self,
        post_id: int,
        user: "User",
        post_data: PostUpdate
    ) -> Post:
        """
        Update an existing post.

        Args:
            post_id: Post ID to update
            user: User object attempting update (for authorization)
            post_data: Post update data

        Returns:
            Updated Post domain model

        Raises:
            NotFoundError: If post not found
            AuthenticationError: If user is not the author or admin
        """
        async with self.db_adapter.session() as session:
            # Get existing post
            result = await session.execute(
                select(PostsTable).where(PostsTable.id == post_id)
            )
            post = result.scalars().first()

            if not post:
                raise NotFoundError(f"Post with ID {post_id} not found")

            # Check authorization (author or admin)
            if post.author_id != user.id and not user.is_admin:
                raise AuthenticationError("You can only edit your own posts (unless admin)")

            # Update fields
            if post_data.title is not None:
                post.title = post_data.title
            if post_data.content is not None:
                post.content = post_data.content

            post.updated_at = datetime.now(timezone.utc)

            await session.flush()
            await session.refresh(post)

            logger.info(
                "Updated post",
                extra={"post_id": post_id, "user_id": user.id, "is_admin": user.is_admin}
            )

            return Post.model_validate(post)

    async def delete_post(self, post_id: int, user: "User") -> None:
        """
        Delete a post.

        Args:
            post_id: Post ID to delete
            user: User object attempting deletion (for authorization)

        Raises:
            NotFoundError: If post not found
            AuthenticationError: If user is not the author or admin
        """
        async with self.db_adapter.session() as session:
            # Get existing post
            result = await session.execute(
                select(PostsTable).where(PostsTable.id == post_id)
            )
            post = result.scalars().first()

            if not post:
                raise NotFoundError(f"Post with ID {post_id} not found")

            # Check authorization (author or admin)
            if post.author_id != user.id and not user.is_admin:
                raise AuthenticationError("You can only delete your own posts (unless admin)")

            await session.delete(post)

            logger.info(
                "Deleted post",
                extra={"post_id": post_id, "user_id": user.id, "is_admin": user.is_admin}
            )

    async def increment_vote_count(
        self,
        post_id: int,
        vote_type: int
    ) -> None:
        """
        Increment vote count for a post.

        Args:
            post_id: Post ID to update
            vote_type: 1 for upvote, -1 for downvote
        """
        async with self.db_adapter.session() as session:
            if vote_type == 1:
                await session.execute(
                    update(PostsTable)
                    .where(PostsTable.id == post_id)
                    .values(upvotes=PostsTable.upvotes + 1)
                )
            elif vote_type == -1:
                await session.execute(
                    update(PostsTable)
                    .where(PostsTable.id == post_id)
                    .values(downvotes=PostsTable.downvotes + 1)
                )

            logger.info(
                "Updated post vote count",
                extra={"post_id": post_id, "vote_type": vote_type}
            )
