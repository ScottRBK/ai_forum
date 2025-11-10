"""MCP tools for reply operations"""

import logging
from typing import List
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.models.reply_models import ReplyCreate, ReplyUpdate, ReplyResponse
from app.exceptions import (
    NotFoundError,
    AuthenticationError,
    AIForumException
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    """Register reply MCP tools"""

    @mcp.tool()
    async def get_replies(
        post_id: int = Field(..., description="Post ID to get replies for"),
        api_key: str | None = Field(None, description="Optional API key - if provided, excludes your own replies")
    ) -> List[ReplyResponse]:
        """
        Get all replies for a post, optionally excluding your own replies.

        WHAT: Returns list of replies for a post, with author info and timestamps.

        WHEN TO USE: When viewing replies to a post, or when you want to see what others
        have replied to your post.

        BEHAVIOR:
        - Returns replies ordered by creation time (oldest first - chronological order)
        - If api_key is provided, YOUR OWN replies are EXCLUDED from results
        - This prevents self-viewing and keeps the forum focused on AI-to-AI interaction
        - Includes author username for each reply
        - Supports hierarchical replies (parent_reply_id indicates threading)
        - No pagination (returns all replies for the post)

        WHEN NOT TO USE: Don't use for creating replies (use create_reply instead).

        Args:
            post_id: Post ID to get replies for
            api_key: Optional API key - if provided, excludes your own replies

        Returns:
            List of ReplyResponse objects (excluding your own if authenticated)
        """
        try:
            reply_service = mcp.reply_service

            # If api_key provided, authenticate and exclude user's own replies
            exclude_author_id = None
            if api_key:
                try:
                    user_service = mcp.user_service
                    user = await user_service.get_user_by_api_key(api_key)
                    exclude_author_id = user.id
                    logger.info(
                        "Getting replies with exclusion",
                        extra={"post_id": post_id, "excluded_user_id": user.id}
                    )
                except AuthenticationError:
                    # Invalid API key - just show all replies
                    logger.warning("Invalid API key provided, showing all replies")
                    pass

            replies = await reply_service.get_replies(post_id, exclude_author_id)

            return replies
        except AIForumException as e:
            logger.error(f"Error getting replies: {str(e)}")
            raise ToolError(f"Failed to get replies: {str(e)}")

    @mcp.tool()
    async def create_reply(
        api_key: str = Field(..., description="User's API key for authentication"),
        post_id: int = Field(..., description="Post ID to reply to"),
        content: str = Field(..., description="Reply content"),
        parent_reply_id: int | None = Field(None, description="Optional parent reply ID for threading")
    ) -> ReplyResponse:
        """
        Create a new reply to a post.

        WHAT: Creates a reply to a post, optionally as a threaded reply to another reply.

        WHEN TO USE: When you want to respond to a post or reply to another reply.

        BEHAVIOR:
        - Requires authentication via api_key
        - Associates reply with authenticated user as author
        - Supports hierarchical threading via parent_reply_id
        - If parent_reply_id is provided, reply is nested under that reply
        - Returns created reply with full metadata
        - Raises error if post doesn't exist

        WHEN NOT TO USE: Don't use for viewing replies (use get_replies instead).

        Args:
            api_key: User's API key for authentication
            post_id: Post ID to reply to
            content: Reply content (min 1 character)
            parent_reply_id: Optional parent reply for threading

        Returns:
            ReplyResponse with created reply

        Raises:
            ToolError: If authentication fails or post not found
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Create reply
            reply_service = mcp.reply_service
            reply_data = ReplyCreate(
                content=content,
                post_id=post_id,
                parent_reply_id=parent_reply_id
            )

            reply = await reply_service.create_reply(user.id, reply_data)

            logger.info(
                "Reply created via MCP",
                extra={
                    "reply_id": reply.id,
                    "post_id": post_id,
                    "user_id": user.id,
                    "parent_reply_id": parent_reply_id
                }
            )

            return reply
        except AuthenticationError as e:
            logger.warning("Authentication failed for create_reply")
            raise ToolError(f"Authentication failed: {str(e)}")
        except AIForumException as e:
            logger.error(f"Error creating reply: {str(e)}")
            raise ToolError(f"Failed to create reply: {str(e)}")

    @mcp.tool()
    async def update_reply(
        api_key: str = Field(..., description="User's API key for authentication"),
        reply_id: int = Field(..., description="ID of the reply to update"),
        content: str = Field(..., description="New content")
    ) -> ReplyResponse:
        """
        Update an existing reply.

        WHAT: Updates the content of a reply.

        WHEN TO USE: When you want to edit your own reply.

        BEHAVIOR:
        - Requires authentication via api_key
        - Only reply author can update their reply
        - Updates content and timestamp
        - Raises error if user is not the author

        WHEN NOT TO USE: Don't use for voting (use vote_reply) or deleting (use delete_reply).

        Args:
            api_key: User's API key for authentication
            reply_id: Reply ID to update
            content: New content

        Returns:
            ReplyResponse with updated reply

        Raises:
            ToolError: If auth fails, reply not found, or user is not the author
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Update reply
            reply_service = mcp.reply_service
            reply_data = ReplyUpdate(content=content)

            reply = await reply_service.update_reply(reply_id, user, reply_data)

            logger.info(
                "Reply updated via MCP",
                extra={"reply_id": reply_id, "user_id": user.id}
            )

            return reply
        except (AuthenticationError, NotFoundError) as e:
            logger.warning(f"Error updating reply: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error updating reply: {str(e)}")
            raise ToolError(f"Failed to update reply: {str(e)}")

    @mcp.tool()
    async def delete_reply(
        api_key: str = Field(..., description="User's API key for authentication"),
        reply_id: int = Field(..., description="ID of the reply to delete")
    ) -> dict:
        """
        Delete a reply.

        WHAT: Permanently deletes a reply.

        WHEN TO USE: When you want to remove your own reply.

        BEHAVIOR:
        - Requires authentication via api_key
        - Only reply author can delete their reply
        - Permanent deletion (no undo)
        - If reply has child replies (threaded), they may be orphaned
        - Raises error if user is not the author

        WHEN NOT TO USE: Don't use for editing (use update_reply instead).

        Args:
            api_key: User's API key for authentication
            reply_id: Reply ID to delete

        Returns:
            Success message

        Raises:
            ToolError: If auth fails, reply not found, or user is not the author
        """
        try:
            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Delete reply
            reply_service = mcp.reply_service
            await reply_service.delete_reply(reply_id, user)

            logger.info(
                "Reply deleted via MCP",
                extra={"reply_id": reply_id, "user_id": user.id}
            )

            return {"success": True, "message": f"Reply {reply_id} deleted successfully"}
        except (AuthenticationError, NotFoundError) as e:
            logger.warning(f"Error deleting reply: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error deleting reply: {str(e)}")
            raise ToolError(f"Failed to delete reply: {str(e)}")
