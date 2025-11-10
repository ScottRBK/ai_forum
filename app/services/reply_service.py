"""Reply service layer"""

import logging
from typing import List

from app.models.reply_models import Reply, ReplyCreate, ReplyUpdate, ReplyResponse
from app.models.user_models import User
from app.repositories.postgres.reply_repository import PostgresReplyRepository
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class ReplyService:
    """Service for reply business logic"""

    def __init__(self, reply_repository: PostgresReplyRepository):
        self.reply_repository = reply_repository

    async def create_reply(self, user_id: int, reply_data: ReplyCreate) -> ReplyResponse:
        """
        Create a new reply.

        Args:
            user_id: ID of the user creating the reply
            reply_data: Reply creation data

        Returns:
            ReplyResponse with created reply
        """
        reply = await self.reply_repository.create_reply(user_id, reply_data)

        # Get full reply data with metadata
        reply_tuple = await self.reply_repository.get_reply_by_id(reply.id)
        if not reply_tuple:
            raise NotFoundError(f"Reply {reply.id} not found after creation")

        reply_obj, author_username = reply_tuple

        return ReplyResponse(
            id=reply_obj.id,
            content=reply_obj.content,
            post_id=reply_obj.post_id,
            author_id=reply_obj.author_id,
            author_username=author_username,
            parent_reply_id=reply_obj.parent_reply_id,
            upvotes=reply_obj.upvotes,
            downvotes=reply_obj.downvotes,
            created_at=reply_obj.created_at,
            updated_at=reply_obj.updated_at
        )

    async def get_replies(
        self,
        post_id: int,
        exclude_author_id: int | None = None
    ) -> List[ReplyResponse]:
        """
        Get all replies for a post, optionally excluding a specific author.

        This implements the key feature from the original AI Forum: when viewing
        replies to a post, the author's own replies are excluded to prevent self-viewing.

        Args:
            post_id: Post ID to get replies for
            exclude_author_id: Optional user ID to exclude (for hiding own replies)

        Returns:
            List of ReplyResponse objects
        """
        replies_data = await self.reply_repository.get_replies(post_id, exclude_author_id)

        return [
            ReplyResponse(
                id=reply.id,
                content=reply.content,
                post_id=reply.post_id,
                author_id=reply.author_id,
                author_username=author_username,
                parent_reply_id=reply.parent_reply_id,
                upvotes=reply.upvotes,
                downvotes=reply.downvotes,
                created_at=reply.created_at,
                updated_at=reply.updated_at
            )
            for reply, author_username in replies_data
        ]

    async def get_reply_by_id(self, reply_id: int) -> ReplyResponse:
        """
        Get a single reply by ID.

        Args:
            reply_id: Reply ID

        Returns:
            ReplyResponse

        Raises:
            NotFoundError: If reply not found
        """
        reply_tuple = await self.reply_repository.get_reply_by_id(reply_id)
        if not reply_tuple:
            raise NotFoundError(f"Reply with ID {reply_id} not found")

        reply, author_username = reply_tuple

        return ReplyResponse(
            id=reply.id,
            content=reply.content,
            post_id=reply.post_id,
            author_id=reply.author_id,
            author_username=author_username,
            parent_reply_id=reply.parent_reply_id,
            upvotes=reply.upvotes,
            downvotes=reply.downvotes,
            created_at=reply.created_at,
            updated_at=reply.updated_at
        )

    async def update_reply(
        self,
        reply_id: int,
        user: "User",
        reply_data: ReplyUpdate
    ) -> ReplyResponse:
        """
        Update an existing reply.

        Args:
            reply_id: Reply ID
            user: User object attempting update
            reply_data: Update data

        Returns:
            Updated ReplyResponse

        Raises:
            NotFoundError: If reply not found
            AuthenticationError: If user is not the author or admin
        """
        reply = await self.reply_repository.update_reply(reply_id, user, reply_data)

        # Get full reply data with metadata
        reply_tuple = await self.reply_repository.get_reply_by_id(reply.id)
        if not reply_tuple:
            raise NotFoundError(f"Reply {reply.id} not found after update")

        reply_obj, author_username = reply_tuple

        return ReplyResponse(
            id=reply_obj.id,
            content=reply_obj.content,
            post_id=reply_obj.post_id,
            author_id=reply_obj.author_id,
            author_username=author_username,
            parent_reply_id=reply_obj.parent_reply_id,
            upvotes=reply_obj.upvotes,
            downvotes=reply_obj.downvotes,
            created_at=reply_obj.created_at,
            updated_at=reply_obj.updated_at
        )

    async def delete_reply(self, reply_id: int, user: "User") -> None:
        """
        Delete a reply.

        Args:
            reply_id: Reply ID
            user: User object attempting deletion

        Raises:
            NotFoundError: If reply not found
            AuthenticationError: If user is not the author or admin
        """
        await self.reply_repository.delete_reply(reply_id, user)
