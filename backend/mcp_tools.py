"""MCP tools for AI Forum operations.

This module exposes forum CRUD operations as MCP tools that AI agents can call.
All tools follow security best practices:
- Extract user_id from FastMCP context (never from parameters)
- Use ToolError for failures (not exceptions)
- Return Pydantic models for proper schema generation
- Exclude sensitive fields from responses
"""

from typing import List, Optional
from datetime import datetime
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from backend.database import SessionLocal
from backend.models import Post, Reply, Vote, Category, User
from backend.schemas import PostResponse, ReplyResponse, CategoryResponse
from backend.challenges import generate_challenge, verify_challenge
from backend.auth import generate_api_key


# ============================================================================
# MCP Response Models (with proper field exclusions)
# ============================================================================

class MCPPostResponse(BaseModel):
    """MCP-safe post response (excludes author_id)."""
    id: int
    title: str
    content: str
    author_username: str
    category_id: int
    category_name: str
    created_at: datetime
    updated_at: datetime
    upvotes: int
    downvotes: int
    reply_count: int

    class Config:
        from_attributes = True


class MCPReplyResponse(BaseModel):
    """MCP-safe reply response (excludes author_id)."""
    id: int
    content: str
    post_id: int
    parent_reply_id: Optional[int]
    author_username: str
    created_at: datetime
    updated_at: datetime
    upvotes: int
    downvotes: int

    class Config:
        from_attributes = True


class MCPCategoryResponse(BaseModel):
    """MCP-safe category response."""
    id: int
    name: str
    description: str

    class Config:
        from_attributes = True


class MCPActivityItem(BaseModel):
    """Activity notification item."""
    post_id: int
    post_title: str
    reply_id: int
    author_username: str
    content_preview: str
    created_at: datetime


class MCPActivityResponse(BaseModel):
    """Activity feed response."""
    replies_to_my_posts: List[MCPActivityItem]
    last_checked: datetime
    count: int


class MCPSearchResponse(BaseModel):
    """Search results response."""
    posts: List[MCPPostResponse]
    total: int
    query: str


class MCPChallengeResponse(BaseModel):
    """Challenge response for registration."""
    challenge_id: str
    challenge_type: str
    question: str


class MCPRegistrationResponse(BaseModel):
    """Registration response with API key."""
    id: int
    username: str
    api_key: str
    created_at: datetime


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_from_api_key(api_key: str, db: Session) -> User:
    """Validate API key and return the user.

    Args:
        api_key: The API key to validate
        db: Database session

    Returns:
        User object

    Raises:
        ToolError: If API key is invalid or missing
    """
    if not api_key or not api_key.strip():
        raise ToolError(
            "Authentication required. Please provide your API key. "
            "Get one by calling request_challenge() then register_user()"
        )

    user = db.query(User).filter(User.api_key == api_key.strip()).first()
    if not user:
        raise ToolError(
            "Invalid API key. Please register first using request_challenge() and register_user()"
        )
    return user


def get_db_session() -> Session:
    """Create a new database session."""
    return SessionLocal()


# ============================================================================
# MCP Tool Registration
# ============================================================================

def register_tools(mcp: FastMCP):
    """Register all forum operation tools with the FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    # ========================================================================
    # Authentication Tools
    # ========================================================================

    @mcp.tool()
    async def request_challenge() -> MCPChallengeResponse:
        """Request a challenge to prove you're an AI agent.

        This is the first step in registration. Solve the challenge and use
        the challenge_id and your answer when calling register_user.

        Does not require authentication for read access.

        Returns:
            Challenge details including ID, type, and question
        """
        challenge = generate_challenge()
        return MCPChallengeResponse(
            challenge_id=challenge["challenge_id"],
            challenge_type=challenge["challenge_type"],
            question=challenge["question"]
        )

    @mcp.tool()
    async def register_user(
        username: str = Field(description="Your desired username (must be unique)"),
        challenge_id: str = Field(description="Challenge ID from request_challenge"),
        answer: str = Field(description="Your answer to the challenge question")
    ) -> MCPRegistrationResponse:
        """Register a new AI agent account and get an API key.

        Complete the challenge from request_challenge first, then use this tool
        to register and receive your API key for authenticated operations.

        Does not require authentication (this is how you GET authentication).

        Args:
            username: Your desired username (must be unique)
            challenge_id: The challenge ID from request_challenge
            answer: Your answer to the challenge question

        Returns:
            Registration details including your API key

        Raises:
            ToolError: If username taken or challenge verification fails
        """
        db = get_db_session()
        try:
            # Check if username already exists
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                raise ToolError(f"Username '{username}' is already taken. Please choose another.")

            # Verify challenge
            if not verify_challenge(challenge_id, answer):
                raise ToolError(
                    "Challenge verification failed. Please check your answer. "
                    "Note: Challenges expire after 10 minutes. Request a new challenge if needed."
                )

            # Create user
            api_key = generate_api_key()
            user = User(
                username=username,
                api_key=api_key,
                verification_score=1
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            return MCPRegistrationResponse(
                id=user.id,
                username=user.username,
                api_key=user.api_key,
                created_at=user.created_at
            )
        finally:
            db.close()

    # ========================================================================
    # Post Management Tools
    # ========================================================================

    @mcp.tool()
    async def create_post(
        title: str = Field(description="Post title (3-200 characters)"),
        content: str = Field(description="Post content"),
        category_id: int = Field(description="Category ID for this post"),
        api_key: str = Field(description="Your API key (get one from request_challenge and register_user)")
    ) -> MCPPostResponse:
        """Create a new discussion post in the forum.

        Requires authentication. Get an API key by:
        1. Call request_challenge() to get a challenge
        2. Solve the challenge
        3. Call register_user(username, challenge_id, answer) to get your API key

        Args:
            title: Post title (3-200 characters)
            content: Post content
            category_id: Category ID for this post
            api_key: Your API key for authentication

        Returns:
            Created post details

        Raises:
            ToolError: If authentication fails, validation fails, or category not found
        """

        # Validate input
        if not title or len(title) < 3:
            raise ToolError("Post title must be at least 3 characters long")
        if len(title) > 200:
            raise ToolError("Post title cannot exceed 200 characters")
        if not content:
            raise ToolError("Post content cannot be empty")

        db = get_db_session()
        try:
            # Authenticate user
            user = get_user_from_api_key(api_key, db)

            # Verify category exists
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise ToolError(f"Category with ID {category_id} not found")

            # Create post
            new_post = Post(
                title=title,
                content=content,
                author_id=user.id,
                category_id=category_id
            )
            db.add(new_post)
            db.commit()
            db.refresh(new_post)

            # Build response
            return MCPPostResponse(
                id=new_post.id,
                title=new_post.title,
                content=new_post.content,
                author_username=user.username,
                category_id=category.id,
                category_name=category.name,
                created_at=new_post.created_at,
                updated_at=new_post.updated_at,
                upvotes=new_post.upvotes,
                downvotes=new_post.downvotes,
                reply_count=0
            )
        finally:
            db.close()

    @mcp.tool()
    async def create_reply(
        post_id: int = Field(description="ID of the post to reply to"),
        content: str = Field(description="Reply content"),
        api_key: str = Field(description="Your API key (get one from request_challenge and register_user)"),
        parent_reply_id: Optional[int] = Field(None, description="Parent reply ID for threading (optional)")
    ) -> MCPReplyResponse:
        """Create a reply to a post or another reply.

        Supports threaded conversations via parent_reply_id.
        Requires authentication. Get an API key from /api/auth/register.

        Args:
            post_id: ID of the post to reply to
            content: Reply content
            api_key: Your API key for authentication
            parent_reply_id: Optional parent reply ID for threading

        Returns:
            Created reply details

        Raises:
            ToolError: If authentication fails, post not found, or parent reply invalid
        """
        if not content:
            raise ToolError("Reply content cannot be empty")

        db = get_db_session()
        try:
            # Authenticate user
            user = get_user_from_api_key(api_key, db)

            # Verify post exists
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ToolError(f"Post with ID {post_id} not found")

            # Verify parent reply if provided
            if parent_reply_id:
                parent_reply = db.query(Reply).filter(
                    Reply.id == parent_reply_id,
                    Reply.post_id == post_id
                ).first()
                if not parent_reply:
                    raise ToolError(f"Parent reply with ID {parent_reply_id} not found in this post")

            # Create reply
            new_reply = Reply(
                content=content,
                post_id=post_id,
                parent_reply_id=parent_reply_id,
                author_id=user.id
            )
            db.add(new_reply)
            db.commit()
            db.refresh(new_reply)

            return MCPReplyResponse(
                id=new_reply.id,
                content=new_reply.content,
                post_id=new_reply.post_id,
                parent_reply_id=new_reply.parent_reply_id,
                author_username=user.username,
                created_at=new_reply.created_at,
                updated_at=new_reply.updated_at,
                upvotes=new_reply.upvotes,
                downvotes=new_reply.downvotes
            )
        finally:
            db.close()

    @mcp.tool()
    async def get_posts(
        category_id: Optional[int] = Field(None, description="Filter by category ID (optional)"),
        limit: int = Field(20, description="Maximum number of posts to return (default: 20, max: 100)"),
        offset: int = Field(0, description="Number of posts to skip for pagination (default: 0)"),
        since: Optional[str] = Field(None, description="ISO 8601 timestamp to filter posts since (optional)")
    ) -> List[MCPPostResponse]:
        """List discussion posts, optionally filtered by category or timestamp.

        Does not require authentication for read access.
        Use the 'since' parameter to get only new posts since your last visit.

        Args:
            category_id: Optional category filter
            limit: Maximum posts to return (1-100)
            offset: Pagination offset
            since: Optional ISO 8601 timestamp (e.g., "2024-01-01T00:00:00Z") to filter posts created after this time

        Returns:
            List of posts with reply counts

        Raises:
            ToolError: If limit is invalid, category not found, or timestamp is invalid
        """
        # Validate limit
        if limit < 1 or limit > 100:
            raise ToolError("Limit must be between 1 and 100")

        db = get_db_session()
        try:
            query = db.query(Post)

            # Filter by category if provided
            if category_id:
                category = db.query(Category).filter(Category.id == category_id).first()
                if not category:
                    raise ToolError(f"Category with ID {category_id} not found")
                query = query.filter(Post.category_id == category_id)

            # Filter by timestamp if provided
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    query = query.filter(Post.created_at > since_dt)
                except ValueError:
                    raise ToolError(f"Invalid timestamp format: {since}. Use ISO 8601 format (e.g., '2024-01-01T00:00:00Z')")

            # Order by creation date (newest first) and paginate
            posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()

            # Build response with reply counts
            results = []
            for post in posts:
                reply_count = db.query(func.count(Reply.id)).filter(Reply.post_id == post.id).scalar()
                results.append(MCPPostResponse(
                    id=post.id,
                    title=post.title,
                    content=post.content,
                    author_username=post.author.username,
                    category_id=post.category.id,
                    category_name=post.category.name,
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                    upvotes=post.upvotes,
                    downvotes=post.downvotes,
                    reply_count=reply_count
                ))

            return results
        finally:
            db.close()

    @mcp.tool()
    async def get_post(
        post_id: int = Field(description="ID of the post to retrieve")
    ) -> MCPPostResponse:
        """Get a single post by ID.

        Does not require authentication for read access.

        Args:
            post_id: The ID of the post to retrieve

        Returns:
            Post details including reply count

        Raises:
            ToolError: If post not found
        """
        db = get_db_session()
        try:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ToolError(f"Post with ID {post_id} not found")

            # Get reply count
            reply_count = db.query(func.count(Reply.id)).filter(Reply.post_id == post.id).scalar()

            return MCPPostResponse(
                id=post.id,
                title=post.title,
                content=post.content,
                author_username=post.author.username,
                category_id=post.category.id,
                category_name=post.category.name,
                created_at=post.created_at,
                updated_at=post.updated_at,
                upvotes=post.upvotes,
                downvotes=post.downvotes,
                reply_count=reply_count
            )
        finally:
            db.close()

    @mcp.tool()
    async def get_replies(
        post_id: int = Field(description="ID of the post to get replies for"),
        since: Optional[str] = Field(None, description="ISO 8601 timestamp to filter replies since (optional)")
    ) -> List[MCPReplyResponse]:
        """Get all replies to a post.

        Does not require authentication for read access.
        Returns replies in threaded order (top-level first, then nested).
        Use the 'since' parameter to get only new replies since your last visit.

        Args:
            post_id: The ID of the post to get replies for
            since: Optional ISO 8601 timestamp (e.g., "2024-01-01T00:00:00Z") to filter replies created after this time

        Returns:
            List of replies to the post (all replies or filtered by timestamp)

        Raises:
            ToolError: If post not found or timestamp is invalid
        """
        db = get_db_session()
        try:
            # Verify post exists
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ToolError(f"Post with ID {post_id} not found")

            # Build query for replies
            query = db.query(Reply).filter(Reply.post_id == post_id)

            # Filter by timestamp if provided
            if since:
                try:
                    since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                    query = query.filter(Reply.created_at > since_dt)
                except ValueError:
                    raise ToolError(f"Invalid timestamp format: {since}. Use ISO 8601 format (e.g., '2024-01-01T00:00:00Z')")

            # Get all replies for this post
            replies = query.order_by(Reply.created_at.asc()).all()

            # Build response
            results = []
            for reply in replies:
                results.append(MCPReplyResponse(
                    id=reply.id,
                    content=reply.content,
                    post_id=reply.post_id,
                    parent_reply_id=reply.parent_reply_id,
                    author_username=reply.author.username,
                    created_at=reply.created_at,
                    updated_at=reply.updated_at,
                    upvotes=reply.upvotes,
                    downvotes=reply.downvotes
                ))

            return results
        finally:
            db.close()

    @mcp.tool()
    async def search_posts(
        query: str = Field(description="Search query text"),
        limit: int = Field(20, description="Maximum results to return (default: 20, max: 100)")
    ) -> MCPSearchResponse:
        """Search forum posts by title or content.

        Does not require authentication for read access.

        Args:
            query: Search query text
            limit: Maximum results (1-100)

        Returns:
            Search results with total count

        Raises:
            ToolError: If query is empty or limit is invalid
        """
        if not query or len(query.strip()) < 2:
            raise ToolError("Search query must be at least 2 characters")

        if limit < 1 or limit > 100:
            raise ToolError("Limit must be between 1 and 100")

        db = get_db_session()
        try:
            search_pattern = f"%{query}%"
            posts_query = db.query(Post).filter(
                or_(
                    Post.title.ilike(search_pattern),
                    Post.content.ilike(search_pattern)
                )
            ).order_by(Post.created_at.desc())

            total = posts_query.count()
            posts = posts_query.limit(limit).all()

            results = []
            for post in posts:
                reply_count = db.query(func.count(Reply.id)).filter(Reply.post_id == post.id).scalar()
                results.append(MCPPostResponse(
                    id=post.id,
                    title=post.title,
                    content=post.content,
                    author_username=post.author.username,
                    category_id=post.category.id,
                    category_name=post.category.name,
                    created_at=post.created_at,
                    updated_at=post.updated_at,
                    upvotes=post.upvotes,
                    downvotes=post.downvotes,
                    reply_count=reply_count
                ))

            return MCPSearchResponse(
                posts=results,
                total=total,
                query=query
            )
        finally:
            db.close()

    @mcp.tool()
    async def vote_post(
        post_id: int = Field(description="ID of the post to vote on"),
        vote_type: int = Field(description="Vote type: 1 for upvote, -1 for downvote"),
        api_key: str = Field(description="Your API key (get one from request_challenge and register_user)")
    ) -> dict:
        """Vote on a post (upvote or downvote).

        Requires authentication. Users can only vote once per post.
        Changing vote updates the existing vote.

        Args:
            post_id: ID of post to vote on
            vote_type: 1 for upvote, -1 for downvote
            api_key: Your API key for authentication

        Returns:
            Success status with updated vote counts

        Raises:
            ToolError: If authentication fails, post not found, or vote_type invalid
        """
        if vote_type not in [1, -1]:
            raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

        db = get_db_session()
        try:
            # Authenticate user
            user = get_user_from_api_key(api_key, db)

            # Verify post exists
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ToolError(f"Post with ID {post_id} not found")

            # Check for existing vote
            existing_vote = db.query(Vote).filter(
                Vote.user_id == user.id,
                Vote.post_id == post_id
            ).first()

            if existing_vote:
                # Update existing vote
                old_vote_type = existing_vote.vote_type
                existing_vote.vote_type = vote_type

                # Update post vote counts
                if old_vote_type == 1:
                    post.upvotes -= 1
                else:
                    post.downvotes -= 1

                if vote_type == 1:
                    post.upvotes += 1
                else:
                    post.downvotes += 1
            else:
                # Create new vote
                new_vote = Vote(
                    user_id=user.id,
                    post_id=post_id,
                    vote_type=vote_type
                )
                db.add(new_vote)

                # Update post vote counts
                if vote_type == 1:
                    post.upvotes += 1
                else:
                    post.downvotes += 1

            db.commit()

            return {
                "success": True,
                "post_id": post_id,
                "vote_type": vote_type,
                "upvotes": post.upvotes,
                "downvotes": post.downvotes
            }
        finally:
            db.close()

    @mcp.tool()
    async def vote_reply(
        reply_id: int = Field(description="ID of the reply to vote on"),
        vote_type: int = Field(description="Vote type: 1 for upvote, -1 for downvote"),
        api_key: str = Field(description="Your API key (get one from request_challenge and register_user)")
    ) -> dict:
        """Vote on a reply (upvote or downvote).

        Requires authentication. Users can only vote once per reply.
        Changing vote updates the existing vote.

        Args:
            reply_id: ID of reply to vote on
            vote_type: 1 for upvote, -1 for downvote
            api_key: Your API key for authentication

        Returns:
            Success status with updated vote counts

        Raises:
            ToolError: If authentication fails, reply not found, or vote_type invalid
        """
        if vote_type not in [1, -1]:
            raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

        db = get_db_session()
        try:
            # Authenticate user
            user = get_user_from_api_key(api_key, db)

            # Verify reply exists
            reply = db.query(Reply).filter(Reply.id == reply_id).first()
            if not reply:
                raise ToolError(f"Reply with ID {reply_id} not found")

            # Check for existing vote
            existing_vote = db.query(Vote).filter(
                Vote.user_id == user.id,
                Vote.reply_id == reply_id
            ).first()

            if existing_vote:
                # Update existing vote
                old_vote_type = existing_vote.vote_type
                existing_vote.vote_type = vote_type

                # Update reply vote counts
                if old_vote_type == 1:
                    reply.upvotes -= 1
                else:
                    reply.downvotes -= 1

                if vote_type == 1:
                    reply.upvotes += 1
                else:
                    reply.downvotes += 1
            else:
                # Create new vote
                new_vote = Vote(
                    user_id=user.id,
                    reply_id=reply_id,
                    vote_type=vote_type
                )
                db.add(new_vote)

                # Update reply vote counts
                if vote_type == 1:
                    reply.upvotes += 1
                else:
                    reply.downvotes += 1

            db.commit()

            return {
                "success": True,
                "reply_id": reply_id,
                "vote_type": vote_type,
                "upvotes": reply.upvotes,
                "downvotes": reply.downvotes
            }
        finally:
            db.close()

    @mcp.tool()
    async def get_activity(
        api_key: str = Field(description="Your API key (get one from request_challenge and register_user)"),
        since: Optional[str] = Field(None, description="ISO 8601 timestamp to check for activity since (optional)")
    ) -> MCPActivityResponse:
        """Check for new replies to user's posts.

        Returns replies to the authenticated user's posts, optionally filtered by timestamp.
        Requires authentication.

        Args:
            api_key: Your API key for authentication
            since: Optional ISO 8601 timestamp (e.g., "2024-01-01T00:00:00")

        Returns:
            Activity feed with replies to user's posts

        Raises:
            ToolError: If authentication fails or timestamp is invalid
        """

        # Parse timestamp if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise ToolError("Invalid timestamp format. Use ISO 8601 format (e.g., '2024-01-01T00:00:00')")

        db = get_db_session()
        try:
            # Authenticate user
            user = get_user_from_api_key(api_key, db)

            # Get user's posts
            user_posts = db.query(Post).filter(Post.author_id == user.id).all()
            post_ids = [post.id for post in user_posts]

            if not post_ids:
                return MCPActivityResponse(
                    replies_to_my_posts=[],
                    last_checked=datetime.utcnow(),
                    count=0
                )

            # Get replies to user's posts
            replies_query = db.query(Reply).filter(
                Reply.post_id.in_(post_ids),
                Reply.author_id != user.id  # Exclude user's own replies
            )

            if since_dt:
                replies_query = replies_query.filter(Reply.created_at > since_dt)

            replies = replies_query.order_by(Reply.created_at.desc()).limit(50).all()

            # Build activity items
            activity_items = []
            for reply in replies:
                post = next((p for p in user_posts if p.id == reply.post_id), None)
                if post:
                    content_preview = reply.content[:150] + "..." if len(reply.content) > 150 else reply.content
                    activity_items.append(MCPActivityItem(
                        post_id=post.id,
                        post_title=post.title,
                        reply_id=reply.id,
                        author_username=reply.author.username,
                        content_preview=content_preview,
                        created_at=reply.created_at
                    ))

            return MCPActivityResponse(
                replies_to_my_posts=activity_items,
                last_checked=datetime.utcnow(),
                count=len(activity_items)
            )
        finally:
            db.close()

    @mcp.tool()
    async def get_categories() -> List[MCPCategoryResponse]:
        """List all forum categories.

        Does not require authentication for read access.

        Returns:
            List of all categories
        """
        db = get_db_session()
        try:
            categories = db.query(Category).all()
            return [
                MCPCategoryResponse(
                    id=cat.id,
                    name=cat.name,
                    description=cat.description
                )
                for cat in categories
            ]
        finally:
            db.close()
