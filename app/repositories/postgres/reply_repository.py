"""Reply repository for database operations"""

import logging
from typing import List
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.reply_models import Reply, ReplyCreate, ReplyUpdate
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import RepliesTable, UsersTable
from app.exceptions import NotFoundError, AuthenticationError

logger = logging.getLogger(__name__)


class PostgresReplyRepository:
    """Repository for reply database operations"""

    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def create_reply(
        self,
        user_id: int,
        reply_data: ReplyCreate
    ) -> Reply:
        """
        Create a new reply.

        Args:
            user_id: ID of the user creating the reply
            reply_data: Reply creation data

        Returns:
            Created Reply domain model
        """
        async with self.db_adapter.session() as session:
            reply = RepliesTable(
                content=reply_data.content,
                post_id=reply_data.post_id,
                parent_reply_id=reply_data.parent_reply_id,
                author_id=user_id
            )

            session.add(reply)
            await session.flush()
            await session.refresh(reply)

            logger.info(
                "Created reply",
                extra={
                    "reply_id": reply.id,
                    "post_id": reply_data.post_id,
                    "author_id": user_id,
                    "parent_reply_id": reply_data.parent_reply_id
                }
            )

            return Reply.model_validate(reply)

    async def get_replies(
        self,
        post_id: int,
        exclude_author_id: int | None = None
    ) -> List[tuple[Reply, str]]:
        """
        Get all replies for a post, optionally excluding a specific author.

        Args:
            post_id: Post ID to get replies for
            exclude_author_id: Optional user ID to exclude (for hiding own replies)

        Returns:
            List of tuples: (Reply, author_username)
        """
        async with self.db_adapter.session() as session:
            query = (
                select(RepliesTable, UsersTable.username)
                .join(UsersTable, RepliesTable.author_id == UsersTable.id)
                .where(RepliesTable.post_id == post_id)
                .order_by(RepliesTable.created_at.asc())
            )

            # Exclude specific author if requested (for hiding own replies)
            if exclude_author_id is not None:
                query = query.where(RepliesTable.author_id != exclude_author_id)

            result = await session.execute(query)
            rows = result.all()

            logger.info(
                "Retrieved replies",
                extra={
                    "post_id": post_id,
                    "count": len(rows),
                    "excluded_author": exclude_author_id
                }
            )

            return [
                (Reply.model_validate(row[0]), row[1])
                for row in rows
            ]

    async def get_reply_by_id(self, reply_id: int) -> tuple[Reply, str] | None:
        """
        Get a single reply by ID with metadata.

        Args:
            reply_id: Reply ID to retrieve

        Returns:
            Tuple of (Reply, author_username) or None
        """
        async with self.db_adapter.session() as session:
            query = (
                select(RepliesTable, UsersTable.username)
                .join(UsersTable, RepliesTable.author_id == UsersTable.id)
                .where(RepliesTable.id == reply_id)
            )

            result = await session.execute(query)
            row = result.first()

            if row:
                logger.info(
                    "Retrieved reply",
                    extra={"reply_id": reply_id}
                )
                return (Reply.model_validate(row[0]), row[1])

            logger.warning(
                "Reply not found",
                extra={"reply_id": reply_id}
            )
            return None

    async def update_reply(
        self,
        reply_id: int,
        user_id: int,
        reply_data: ReplyUpdate
    ) -> Reply:
        """
        Update an existing reply.

        Args:
            reply_id: Reply ID to update
            user_id: ID of user attempting update (for authorization)
            reply_data: Reply update data

        Returns:
            Updated Reply domain model

        Raises:
            NotFoundError: If reply not found
            AuthenticationError: If user is not the author
        """
        async with self.db_adapter.session() as session:
            # Get existing reply
            result = await session.execute(
                select(RepliesTable).where(RepliesTable.id == reply_id)
            )
            reply = result.scalars().first()

            if not reply:
                raise NotFoundError(f"Reply with ID {reply_id} not found")

            # Check authorization
            if reply.author_id != user_id:
                raise AuthenticationError("You can only edit your own replies")

            # Update content
            reply.content = reply_data.content
            reply.updated_at = datetime.now(timezone.utc)

            await session.flush()
            await session.refresh(reply)

            logger.info(
                "Updated reply",
                extra={"reply_id": reply_id, "user_id": user_id}
            )

            return Reply.model_validate(reply)

    async def delete_reply(self, reply_id: int, user_id: int) -> None:
        """
        Delete a reply.

        Args:
            reply_id: Reply ID to delete
            user_id: ID of user attempting deletion (for authorization)

        Raises:
            NotFoundError: If reply not found
            AuthenticationError: If user is not the author
        """
        async with self.db_adapter.session() as session:
            # Get existing reply
            result = await session.execute(
                select(RepliesTable).where(RepliesTable.id == reply_id)
            )
            reply = result.scalars().first()

            if not reply:
                raise NotFoundError(f"Reply with ID {reply_id} not found")

            # Check authorization
            if reply.author_id != user_id:
                raise AuthenticationError("You can only delete your own replies")

            await session.delete(reply)

            logger.info(
                "Deleted reply",
                extra={"reply_id": reply_id, "user_id": user_id}
            )

    async def increment_vote_count(
        self,
        reply_id: int,
        vote_type: int
    ) -> None:
        """
        Increment vote count for a reply.

        Args:
            reply_id: Reply ID to update
            vote_type: 1 for upvote, -1 for downvote
        """
        async with self.db_adapter.session() as session:
            if vote_type == 1:
                await session.execute(
                    update(RepliesTable)
                    .where(RepliesTable.id == reply_id)
                    .values(upvotes=RepliesTable.upvotes + 1)
                )
            elif vote_type == -1:
                await session.execute(
                    update(RepliesTable)
                    .where(RepliesTable.id == reply_id)
                    .values(downvotes=RepliesTable.downvotes + 1)
                )

            logger.info(
                "Updated reply vote count",
                extra={"reply_id": reply_id, "vote_type": vote_type}
            )
