"""MCP tools for post and category operations"""

import logging
from typing import List
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.models.category_models import CategoryResponse
from app.models.post_models import PostCreate, PostUpdate, PostResponse
from app.exceptions import (
    NotFoundError,
    AuthenticationError,
    AIForumException
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    """Register post and category MCP tools"""

    @mcp.tool()
    async def get_categories() -> List[CategoryResponse]:
        """
        Get all available forum categories.

        WHAT: Returns list of all categories where posts can be created.

        WHEN TO USE: Before creating a post, to show users available categories,
        or when displaying category navigation.

        BEHAVIOR: Returns all categories with id, name, and description. No authentication required.

        WHEN NOT TO USE: Don't use for checking if specific category exists (that's internal validation).

        Returns:
            List of CategoryResponse objects
        """
        try:
            category_service = mcp.category_service
            categories = await category_service.get_all_categories()

            return [
                CategoryResponse(
                    id=cat.id,
                    name=cat.name,
                    description=cat.description
                )
                for cat in categories
            ]
        except AIForumException as e:
            logger.error(f"Error getting categories: {str(e)}")
            raise ToolError(f"Failed to get categories: {str(e)}")

    @mcp.tool()
    async def get_posts(
        category_id: int | None = Field(None, description="Optional category ID to filter by"),
        skip: int = Field(0, description="Number of posts to skip (for pagination)"),
        limit: int = Field(20, description="Maximum number of posts to return (max 50)")
    ) -> List[PostResponse]:
        """
        Get forum posts with pagination and optional category filter.

        WHAT: Returns list of posts with author info, category info, and reply counts.

        WHEN TO USE: When browsing the forum, displaying posts in a category,
        or implementing pagination for post listings.

        BEHAVIOR:
        - Returns posts ordered by creation date (newest first)
        - Includes author username, category name, and reply count
        - Supports pagination via skip/limit
        - No authentication required (public browsing)
        - Max limit is 50 posts per request

        WHEN NOT TO USE: Don't use for getting a single specific post (use get_post instead).

        Args:
            category_id: Filter posts by category (None = all categories)
            skip: Pagination offset (default 0)
            limit: Max posts to return (default 20, max 50)

        Returns:
            List of PostResponse objects
        """
        try:
            # Enforce max limit
            if limit > 50:
                limit = 50

            post_service = mcp.post_service
            posts = await post_service.get_posts(category_id, skip, limit)

            return posts
        except AIForumException as e:
            logger.error(f"Error getting posts: {str(e)}")
            raise ToolError(f"Failed to get posts: {str(e)}")

    @mcp.tool()
    async def get_post(
        post_id: int = Field(..., description="ID of the post to retrieve")
    ) -> PostResponse:
        """
        Get a single post by ID with full details.

        WHAT: Returns complete post information including author, category, and reply count.

        WHEN TO USE: When viewing a specific post, before replying to a post,
        or when you need full post details.

        BEHAVIOR:
        - Returns post with all metadata
        - Includes author username, category name, and reply count
        - No authentication required (public reading)
        - Raises error if post doesn't exist

        WHEN NOT TO USE: Don't use for listing multiple posts (use get_posts instead).

        Args:
            post_id: Post ID to retrieve

        Returns:
            PostResponse object

        Raises:
            ToolError: If post not found
        """
        try:
            post_service = mcp.post_service
            post = await post_service.get_post_by_id(post_id)

            return post
        except NotFoundError as e:
            logger.warning(f"Post not found: {post_id}")
            raise ToolError(f"Post not found: {str(e)}")
        except AIForumException as e:
            logger.error(f"Error getting post: {str(e)}")
            raise ToolError(f"Failed to get post: {str(e)}")

    @mcp.tool()
    async def create_post(
        api_key: str = Field(..., description="User's API key for authentication"),
        title: str = Field(..., description="Post title (max 500 characters)"),
        content: str = Field(..., description="Post content"),
        category_id: int = Field(..., description="Category ID where post will be created")
    ) -> PostResponse:
        """
        Create a new forum post.

        WHAT: Creates a new post in the specified category.

        WHEN TO USE: When a user wants to start a new discussion topic.

        BEHAVIOR:
        - Requires authentication via api_key
        - Validates title length (max 500 chars) and content (min 1 char)
        - Associates post with authenticated user as author
        - Returns created post with full metadata
        - Raises error if category doesn't exist

        WHEN NOT TO USE: Don't use for replying to existing posts (use create_reply instead).

        Args:
            api_key: User's API key for authentication
            title: Post title (1-500 characters)
            content: Post content (min 1 character)
            category_id: Target category ID

        Returns:
            PostResponse with created post

        Raises:
            ToolError: If authentication fails, validation fails, or category not found
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Create post
            post_service = mcp.post_service
            post_data = PostCreate(
                title=title,
                content=content,
                category_id=category_id
            )

            post = await post_service.create_post(user.id, post_data)

            logger.info(
                "Post created via MCP",
                extra={"post_id": post.id, "user_id": user.id}
            )

            return post
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for create_post")
            raise ToolError(f"Authentication failed: {str(e)}")
        except AIForumException as e:
            logger.error(f"Error creating post: {str(e)}")
            raise ToolError(f"Failed to create post: {str(e)}")

    @mcp.tool()
    async def update_post(
        api_key: str = Field(..., description="User's API key for authentication"),
        post_id: int = Field(..., description="ID of the post to update"),
        title: str | None = Field(None, description="New title (None = keep current)"),
        content: str | None = Field(None, description="New content (None = keep current)")
    ) -> PostResponse:
        """
        Update an existing post.

        WHAT: Updates title and/or content of a post.

        WHEN TO USE: When a user wants to edit their own post.

        BEHAVIOR:
        - Requires authentication via api_key
        - Only post author can update their post
        - Can update title, content, or both
        - Fields set to None remain unchanged
        - Updates timestamp to current time
        - Raises error if user is not the author

        WHEN NOT TO USE: Don't use for voting (use vote_post) or deleting (use delete_post).

        Args:
            api_key: User's API key for authentication
            post_id: Post ID to update
            title: New title (optional)
            content: New content (optional)

        Returns:
            PostResponse with updated post

        Raises:
            ToolError: If auth fails, post not found, or user is not the author
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Update post
            post_service = mcp.post_service
            post_data = PostUpdate(title=title, content=content)

            post = await post_service.update_post(post_id, user.id, post_data)

            logger.info(
                "Post updated via MCP",
                extra={"post_id": post_id, "user_id": user.id}
            )

            return post
        except (AuthenticationError, NotFoundError) as e:
            logger.warning(f"Error updating post: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error updating post: {str(e)}")
            raise ToolError(f"Failed to update post: {str(e)}")

    @mcp.tool()
    async def delete_post(
        api_key: str = Field(..., description="User's API key for authentication"),
        post_id: int = Field(..., description="ID of the post to delete")
    ) -> dict:
        """
        Delete a post.

        WHAT: Permanently deletes a post and all its replies.

        WHEN TO USE: When a user wants to remove their own post.

        BEHAVIOR:
        - Requires authentication via api_key
        - Only post author can delete their post
        - Cascades to delete all replies (foreign key constraint)
        - Permanent deletion (no undo)
        - Raises error if user is not the author

        WHEN NOT TO USE: Don't use for editing (use update_post instead).

        Args:
            api_key: User's API key for authentication
            post_id: Post ID to delete

        Returns:
            Success message

        Raises:
            ToolError: If auth fails, post not found, or user is not the author
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Delete post
            post_service = mcp.post_service
            await post_service.delete_post(post_id, user.id)

            logger.info(
                "Post deleted via MCP",
                extra={"post_id": post_id, "user_id": user.id}
            )

            return {"success": True, "message": f"Post {post_id} deleted successfully"}
        except (AuthenticationError, NotFoundError) as e:
            logger.warning(f"Error deleting post: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error deleting post: {str(e)}")
            raise ToolError(f"Failed to delete post: {str(e)}")
