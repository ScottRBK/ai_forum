"""Vote repository for database operations"""

import logging
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.models.vote_models import Vote, VoteCreate
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import VotesTable
from app.repositories.postgres.post_repository import PostgresPostRepository
from app.repositories.postgres.reply_repository import PostgresReplyRepository
from app.exceptions import DuplicateError, NotFoundError

logger = logging.getLogger(__name__)


class PostgresVoteRepository:
    """Repository for vote database operations"""

    def __init__(
        self,
        db_adapter: PostgresDatabaseAdapter,
        post_repository: PostgresPostRepository,
        reply_repository: PostgresReplyRepository
    ):
        self.db_adapter = db_adapter
        self.post_repository = post_repository
        self.reply_repository = reply_repository

    async def create_vote(
        self,
        user_id: int,
        vote_data: VoteCreate
    ) -> Vote:
        """
        Create a new vote and update the corresponding post/reply vote count.

        Args:
            user_id: ID of the user voting
            vote_data: Vote creation data

        Returns:
            Created Vote domain model

        Raises:
            DuplicateError: If user has already voted on this item
            NotFoundError: If post/reply doesn't exist
        """
        async with self.db_adapter.session() as session:
            # Check for duplicate vote
            existing_vote = await self._get_existing_vote(user_id, vote_data)
            if existing_vote:
                item_type = "post" if vote_data.post_id else "reply"
                item_id = vote_data.post_id or vote_data.reply_id
                raise DuplicateError(
                    f"You have already voted on this {item_type} (ID: {item_id})"
                )

            # Create vote
            vote = VotesTable(
                user_id=user_id,
                post_id=vote_data.post_id,
                reply_id=vote_data.reply_id,
                vote_type=vote_data.vote_type
            )

            session.add(vote)
            await session.flush()
            await session.refresh(vote)

            logger.info(
                "Created vote",
                extra={
                    "vote_id": vote.id,
                    "user_id": user_id,
                    "post_id": vote_data.post_id,
                    "reply_id": vote_data.reply_id,
                    "vote_type": vote_data.vote_type
                }
            )

            # Update vote count on post/reply
            if vote_data.post_id:
                await self.post_repository.increment_vote_count(
                    vote_data.post_id,
                    vote_data.vote_type
                )
            else:
                await self.reply_repository.increment_vote_count(
                    vote_data.reply_id,
                    vote_data.vote_type
                )

            return Vote.model_validate(vote)

    async def _get_existing_vote(
        self,
        user_id: int,
        vote_data: VoteCreate
    ) -> Vote | None:
        """
        Check if user has already voted on this post/reply.

        Args:
            user_id: User ID
            vote_data: Vote data to check

        Returns:
            Existing Vote or None
        """
        async with self.db_adapter.session() as session:
            if vote_data.post_id:
                query = select(VotesTable).where(
                    and_(
                        VotesTable.user_id == user_id,
                        VotesTable.post_id == vote_data.post_id
                    )
                )
            else:
                query = select(VotesTable).where(
                    and_(
                        VotesTable.user_id == user_id,
                        VotesTable.reply_id == vote_data.reply_id
                    )
                )

            result = await session.execute(query)
            vote_orm = result.scalars().first()

            if vote_orm:
                return Vote.model_validate(vote_orm)
            return None

    async def get_user_votes(
        self,
        user_id: int,
        post_id: int | None = None,
        reply_id: int | None = None
    ) -> list[Vote]:
        """
        Get all votes by a user, optionally filtered by post or reply.

        Args:
            user_id: User ID
            post_id: Optional post ID filter
            reply_id: Optional reply ID filter

        Returns:
            List of Vote domain models
        """
        async with self.db_adapter.session() as session:
            query = select(VotesTable).where(VotesTable.user_id == user_id)

            if post_id is not None:
                query = query.where(VotesTable.post_id == post_id)
            if reply_id is not None:
                query = query.where(VotesTable.reply_id == reply_id)

            result = await session.execute(query)
            votes = result.scalars().all()

            logger.info(
                "Retrieved user votes",
                extra={
                    "user_id": user_id,
                    "count": len(votes),
                    "post_id": post_id,
                    "reply_id": reply_id
                }
            )

            return [Vote.model_validate(vote) for vote in votes]
