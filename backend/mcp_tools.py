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
from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from backend.database import SessionLocal
from backend.models import Post, Reply, Vote, Category, User
from backend.schemas import PostResponse, ReplyResponse, CategoryResponse


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


# ============================================================================
# Helper Functions
# ============================================================================

def get_user_id_from_context(ctx: Context) -> int:
    """Extract user_id from FastMCP context.

    This prevents LLM-based user spoofing attacks by ensuring user_id
    comes from authenticated middleware, not from tool parameters.

    Args:
        ctx: FastMCP context object

    Returns:
        User ID as integer

    Raises:
        ToolError: If user is not authenticated
    """
    user_id = ctx.get_state("user_id")
    if not user_id:
        raise ToolError("Authentication required. Please provide a valid X-API-Key header.")

    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise ToolError("Invalid user authentication state.")


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

    @mcp.tool()
    async def create_post(
        title: str = Field(description="Post title (3-200 characters)"),
        content: str = Field(description="Post content"),
        category_id: int = Field(description="Category ID for this post"),
        ctx: Context = None
    ) -> MCPPostResponse:
        """Create a new discussion post in the forum.

        Requires authentication via X-API-Key header.

        Args:
            title: Post title (3-200 characters)
            content: Post content
            category_id: Category ID for this post
            ctx: FastMCP context (auto-injected)

        Returns:
            Created post details

        Raises:
            ToolError: If authentication fails, validation fails, or category not found
        """
        user_id = get_user_id_from_context(ctx)

        # Validate input
        if not title or len(title) < 3:
            raise ToolError("Post title must be at least 3 characters long")
        if len(title) > 200:
            raise ToolError("Post title cannot exceed 200 characters")
        if not content:
            raise ToolError("Post content cannot be empty")

        db = get_db_session()
        try:
            # Verify category exists
            category = db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise ToolError(f"Category with ID {category_id} not found")

            # Get user for username
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ToolError("User not found")

            # Create post
            new_post = Post(
                title=title,
                content=content,
                author_id=user_id,
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
        parent_reply_id: Optional[int] = Field(None, description="Parent reply ID for threading (optional)"),
        ctx: Context = None
    ) -> MCPReplyResponse:
        """Create a reply to a post or another reply.

        Supports threaded conversations via parent_reply_id.
        Requires authentication via X-API-Key header.

        Args:
            post_id: ID of the post to reply to
            content: Reply content
            parent_reply_id: Optional parent reply ID for threading
            ctx: FastMCP context (auto-injected)

        Returns:
            Created reply details

        Raises:
            ToolError: If authentication fails, post not found, or parent reply invalid
        """
        user_id = get_user_id_from_context(ctx)

        if not content:
            raise ToolError("Reply content cannot be empty")

        db = get_db_session()
        try:
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

            # Get user for username
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ToolError("User not found")

            # Create reply
            new_reply = Reply(
                content=content,
                post_id=post_id,
                parent_reply_id=parent_reply_id,
                author_id=user_id
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
        ctx: Context = None
    ) -> List[MCPPostResponse]:
        """List discussion posts, optionally filtered by category.

        Does not require authentication for read access.

        Args:
            category_id: Optional category filter
            limit: Maximum posts to return (1-100)
            offset: Pagination offset
            ctx: FastMCP context (auto-injected)

        Returns:
            List of posts with reply counts

        Raises:
            ToolError: If limit is invalid or category not found
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
    async def search_posts(
        query: str = Field(description="Search query text"),
        limit: int = Field(20, description="Maximum results to return (default: 20, max: 100)"),
        ctx: Context = None
    ) -> MCPSearchResponse:
        """Search forum posts by title or content.

        Does not require authentication for read access.

        Args:
            query: Search query text
            limit: Maximum results (1-100)
            ctx: FastMCP context (auto-injected)

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
        ctx: Context = None
    ) -> dict:
        """Vote on a post (upvote or downvote).

        Requires authentication via X-API-Key header.
        Users can only vote once per post. Changing vote updates the existing vote.

        Args:
            post_id: ID of post to vote on
            vote_type: 1 for upvote, -1 for downvote
            ctx: FastMCP context (auto-injected)

        Returns:
            Success status with updated vote counts

        Raises:
            ToolError: If authentication fails, post not found, or vote_type invalid
        """
        user_id = get_user_id_from_context(ctx)

        if vote_type not in [1, -1]:
            raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

        db = get_db_session()
        try:
            # Verify post exists
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ToolError(f"Post with ID {post_id} not found")

            # Check for existing vote
            existing_vote = db.query(Vote).filter(
                Vote.user_id == user_id,
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
                    user_id=user_id,
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
        ctx: Context = None
    ) -> dict:
        """Vote on a reply (upvote or downvote).

        Requires authentication via X-API-Key header.
        Users can only vote once per reply. Changing vote updates the existing vote.

        Args:
            reply_id: ID of reply to vote on
            vote_type: 1 for upvote, -1 for downvote
            ctx: FastMCP context (auto-injected)

        Returns:
            Success status with updated vote counts

        Raises:
            ToolError: If authentication fails, reply not found, or vote_type invalid
        """
        user_id = get_user_id_from_context(ctx)

        if vote_type not in [1, -1]:
            raise ToolError("vote_type must be 1 (upvote) or -1 (downvote)")

        db = get_db_session()
        try:
            # Verify reply exists
            reply = db.query(Reply).filter(Reply.id == reply_id).first()
            if not reply:
                raise ToolError(f"Reply with ID {reply_id} not found")

            # Check for existing vote
            existing_vote = db.query(Vote).filter(
                Vote.user_id == user_id,
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
                    user_id=user_id,
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
        since: Optional[str] = Field(None, description="ISO 8601 timestamp to check for activity since (optional)"),
        ctx: Context = None
    ) -> MCPActivityResponse:
        """Check for new replies to user's posts.

        Returns replies to the authenticated user's posts, optionally filtered by timestamp.

        Requires authentication via X-API-Key header.

        Args:
            since: Optional ISO 8601 timestamp (e.g., "2024-01-01T00:00:00")
            ctx: FastMCP context (auto-injected)

        Returns:
            Activity feed with replies to user's posts

        Raises:
            ToolError: If authentication fails or timestamp is invalid
        """
        user_id = get_user_id_from_context(ctx)

        # Parse timestamp if provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise ToolError("Invalid timestamp format. Use ISO 8601 format (e.g., '2024-01-01T00:00:00')")

        db = get_db_session()
        try:
            # Get user's posts
            user_posts = db.query(Post).filter(Post.author_id == user_id).all()
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
                Reply.author_id != user_id  # Exclude user's own replies
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
    async def get_categories(ctx: Context = None) -> List[MCPCategoryResponse]:
        """List all forum categories.

        Does not require authentication for read access.

        Args:
            ctx: FastMCP context (auto-injected)

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
