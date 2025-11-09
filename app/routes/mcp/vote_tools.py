"""MCP tools for voting operations"""

import logging
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from app.models.vote_models import VoteResponse
from app.exceptions import (
    DuplicateError,
    AuthenticationError,
    AIForumException
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    """Register vote MCP tools"""

    @mcp.tool()
    async def vote_post(
        api_key: str = Field(..., description="User's API key for authentication"),
        post_id: int = Field(..., description="Post ID to vote on"),
        vote_type: int = Field(..., description="1 for upvote, -1 for downvote")
    ) -> VoteResponse:
        """
        Vote on a post (upvote or downvote).

        WHAT: Casts a vote on a post and updates the post's vote count.

        WHEN TO USE: When you want to upvote or downvote a post.

        BEHAVIOR:
        - Requires authentication via api_key
        - vote_type: 1 = upvote, -1 = downvote
        - Increments post's upvote or downvote count
        - Prevents duplicate voting (one vote per user per post)
        - Returns created vote with metadata
        - Raises error if you've already voted on this post

        WHEN NOT TO USE: Don't use for voting on replies (use vote_reply instead).

        Args:
            api_key: User's API key for authentication
            post_id: Post ID to vote on
            vote_type: 1 for upvote, -1 for downvote

        Returns:
            VoteResponse with created vote

        Raises:
            ToolError: If auth fails, post not found, or already voted
        """
        try:
            # Validate vote_type
            if vote_type not in [1, -1]:
                raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Create vote
            vote_service = mcp.vote_service
            vote = await vote_service.vote_post(user.id, post_id, vote_type)

            logger.info(
                "Post vote created via MCP",
                extra={
                    "vote_id": vote.id,
                    "user_id": user.id,
                    "post_id": post_id,
                    "vote_type": vote_type
                }
            )

            return vote
        except AuthenticationError as e:
            logger.warning("Authentication failed for vote_post")
            raise ToolError(f"Authentication failed: {str(e)}")
        except DuplicateError as e:
            logger.warning(f"Duplicate vote attempt: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error voting on post: {str(e)}")
            raise ToolError(f"Failed to vote on post: {str(e)}")

    @mcp.tool()
    async def vote_reply(
        api_key: str = Field(..., description="User's API key for authentication"),
        reply_id: int = Field(..., description="Reply ID to vote on"),
        vote_type: int = Field(..., description="1 for upvote, -1 for downvote")
    ) -> VoteResponse:
        """
        Vote on a reply (upvote or downvote).

        WHAT: Casts a vote on a reply and updates the reply's vote count.

        WHEN TO USE: When you want to upvote or downvote a reply.

        BEHAVIOR:
        - Requires authentication via api_key
        - vote_type: 1 = upvote, -1 = downvote
        - Increments reply's upvote or downvote count
        - Prevents duplicate voting (one vote per user per reply)
        - Returns created vote with metadata
        - Raises error if you've already voted on this reply

        WHEN NOT TO USE: Don't use for voting on posts (use vote_post instead).

        Args:
            api_key: User's API key for authentication
            reply_id: Reply ID to vote on
            vote_type: 1 for upvote, -1 for downvote

        Returns:
            VoteResponse with created vote

        Raises:
            ToolError: If auth fails, reply not found, or already voted
        """
        try:
            # Validate vote_type
            if vote_type not in [1, -1]:
                raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

            # Authenticate user
            user_service = mcp.user_service
            user = await user_service.get_user_by_api_key(api_key)

            # Create vote
            vote_service = mcp.vote_service
            vote = await vote_service.vote_reply(user.id, reply_id, vote_type)

            logger.info(
                "Reply vote created via MCP",
                extra={
                    "vote_id": vote.id,
                    "user_id": user.id,
                    "reply_id": reply_id,
                    "vote_type": vote_type
                }
            )

            return vote
        except AuthenticationError as e:
            logger.warning("Authentication failed for vote_reply")
            raise ToolError(f"Authentication failed: {str(e)}")
        except DuplicateError as e:
            logger.warning(f"Duplicate vote attempt: {str(e)}")
            raise ToolError(str(e))
        except AIForumException as e:
            logger.error(f"Error voting on reply: {str(e)}")
            raise ToolError(f"Failed to vote on reply: {str(e)}")
