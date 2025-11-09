"""Post service layer"""

import logging
from typing import List

from app.models.post_models import Post, PostCreate, PostUpdate, PostResponse
from app.repositories.postgres.post_repository import PostgresPostRepository
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class PostService:
    """Service for post business logic"""

    def __init__(self, post_repository: PostgresPostRepository):
        self.post_repository = post_repository

    async def create_post(self, user_id: int, post_data: PostCreate) -> PostResponse:
        """
        Create a new post.

        Args:
            user_id: ID of the user creating the post
            post_data: Post creation data

        Returns:
            PostResponse with created post
        """
        post = await self.post_repository.create_post(user_id, post_data)

        # Get full post data with metadata
        post_tuple = await self.post_repository.get_post_by_id(post.id)
        if not post_tuple:
            raise NotFoundError(f"Post {post.id} not found after creation")

        post_obj, author_username, category_name, reply_count = post_tuple

        return PostResponse(
            id=post_obj.id,
            title=post_obj.title,
            content=post_obj.content,
            category_id=post_obj.category_id,
            category_name=category_name,
            author_id=post_obj.author_id,
            author_username=author_username,
            upvotes=post_obj.upvotes,
            downvotes=post_obj.downvotes,
            reply_count=reply_count,
            created_at=post_obj.created_at,
            updated_at=post_obj.updated_at
        )

    async def get_posts(
        self,
        category_id: int | None = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[PostResponse]:
        """
        Get posts with pagination and optional category filter.

        Args:
            category_id: Optional category filter
            skip: Number of posts to skip
            limit: Maximum number of posts

        Returns:
            List of PostResponse objects
        """
        posts_data = await self.post_repository.get_posts(category_id, skip, limit)

        return [
            PostResponse(
                id=post.id,
                title=post.title,
                content=post.content,
                category_id=post.category_id,
                category_name=category_name,
                author_id=post.author_id,
                author_username=author_username,
                upvotes=post.upvotes,
                downvotes=post.downvotes,
                reply_count=reply_count,
                created_at=post.created_at,
                updated_at=post.updated_at
            )
            for post, author_username, category_name, reply_count in posts_data
        ]

    async def get_post_by_id(self, post_id: int) -> PostResponse:
        """
        Get a single post by ID.

        Args:
            post_id: Post ID

        Returns:
            PostResponse

        Raises:
            NotFoundError: If post not found
        """
        post_tuple = await self.post_repository.get_post_by_id(post_id)
        if not post_tuple:
            raise NotFoundError(f"Post with ID {post_id} not found")

        post, author_username, category_name, reply_count = post_tuple

        return PostResponse(
            id=post.id,
            title=post.title,
            content=post.content,
            category_id=post.category_id,
            category_name=category_name,
            author_id=post.author_id,
            author_username=author_username,
            upvotes=post.upvotes,
            downvotes=post.downvotes,
            reply_count=reply_count,
            created_at=post.created_at,
            updated_at=post.updated_at
        )

    async def update_post(
        self,
        post_id: int,
        user_id: int,
        post_data: PostUpdate
    ) -> PostResponse:
        """
        Update an existing post.

        Args:
            post_id: Post ID
            user_id: ID of user attempting update
            post_data: Update data

        Returns:
            Updated PostResponse

        Raises:
            NotFoundError: If post not found
            AuthenticationError: If user is not the author
        """
        post = await self.post_repository.update_post(post_id, user_id, post_data)

        # Get full post data with metadata
        post_tuple = await self.post_repository.get_post_by_id(post.id)
        if not post_tuple:
            raise NotFoundError(f"Post {post.id} not found after update")

        post_obj, author_username, category_name, reply_count = post_tuple

        return PostResponse(
            id=post_obj.id,
            title=post_obj.title,
            content=post_obj.content,
            category_id=post_obj.category_id,
            category_name=category_name,
            author_id=post_obj.author_id,
            author_username=author_username,
            upvotes=post_obj.upvotes,
            downvotes=post_obj.downvotes,
            reply_count=reply_count,
            created_at=post_obj.created_at,
            updated_at=post_obj.updated_at
        )

    async def delete_post(self, post_id: int, user_id: int) -> None:
        """
        Delete a post.

        Args:
            post_id: Post ID
            user_id: ID of user attempting deletion

        Raises:
            NotFoundError: If post not found
            AuthenticationError: If user is not the author
        """
        await self.post_repository.delete_post(post_id, user_id)
