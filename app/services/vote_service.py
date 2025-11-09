"""Vote service layer"""

import logging

from app.models.vote_models import Vote, VoteCreate, VoteResponse
from app.repositories.postgres.vote_repository import PostgresVoteRepository

logger = logging.getLogger(__name__)


class VoteService:
    """Service for vote business logic"""

    def __init__(self, vote_repository: PostgresVoteRepository):
        self.vote_repository = vote_repository

    async def vote_post(self, user_id: int, post_id: int, vote_type: int) -> VoteResponse:
        """
        Vote on a post.

        Args:
            user_id: ID of the user voting
            post_id: Post ID to vote on
            vote_type: 1 for upvote, -1 for downvote

        Returns:
            VoteResponse with created vote

        Raises:
            DuplicateError: If user has already voted on this post
        """
        vote_data = VoteCreate(
            post_id=post_id,
            vote_type=vote_type
        )

        vote = await self.vote_repository.create_vote(user_id, vote_data)

        return VoteResponse(
            id=vote.id,
            user_id=vote.user_id,
            post_id=vote.post_id,
            reply_id=vote.reply_id,
            vote_type=vote.vote_type,
            created_at=vote.created_at
        )

    async def vote_reply(self, user_id: int, reply_id: int, vote_type: int) -> VoteResponse:
        """
        Vote on a reply.

        Args:
            user_id: ID of the user voting
            reply_id: Reply ID to vote on
            vote_type: 1 for upvote, -1 for downvote

        Returns:
            VoteResponse with created vote

        Raises:
            DuplicateError: If user has already voted on this reply
        """
        vote_data = VoteCreate(
            reply_id=reply_id,
            vote_type=vote_type
        )

        vote = await self.vote_repository.create_vote(user_id, vote_data)

        return VoteResponse(
            id=vote.id,
            user_id=vote.user_id,
            post_id=vote.post_id,
            reply_id=vote.reply_id,
            vote_type=vote.vote_type,
            created_at=vote.created_at
        )

    async def get_user_votes(
        self,
        user_id: int,
        post_id: int | None = None,
        reply_id: int | None = None
    ) -> list[VoteResponse]:
        """
        Get all votes by a user, optionally filtered.

        Args:
            user_id: User ID
            post_id: Optional post ID filter
            reply_id: Optional reply ID filter

        Returns:
            List of VoteResponse objects
        """
        votes = await self.vote_repository.get_user_votes(user_id, post_id, reply_id)

        return [
            VoteResponse(
                id=vote.id,
                user_id=vote.user_id,
                post_id=vote.post_id,
                reply_id=vote.reply_id,
                vote_type=vote.vote_type,
                created_at=vote.created_at
            )
            for vote in votes
        ]
