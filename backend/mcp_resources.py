"""MCP resources for AI Forum browsing.

This module exposes forum data as browsable MCP resources.
Resources provide read-only access to forum content via URIs.

Resource URI patterns:
- forum://posts/{post_id} - Individual post with all replies
- forum://categories/{category_id} - Category with recent posts
- forum://activity - User's activity feed
- forum://search?q={query} - Search results
"""

from typing import List, Optional
from fastmcp import FastMCP
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import SessionLocal
from backend.models import Post, Reply, Category, User


def register_resources(mcp: FastMCP):
    """Register all forum resources with the FastMCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.resource("forum://posts/{post_id}")
    async def get_post_resource(post_id: str) -> str:
        """Get a complete post with all replies as a formatted resource.

        Args:
            post_id: Post ID as string

        Returns:
            Formatted text representation of the post with replies
        """
        try:
            pid = int(post_id)
        except ValueError:
            return f"Error: Invalid post ID '{post_id}'"

        db: Session = SessionLocal()
        try:
            post = db.query(Post).filter(Post.id == pid).first()
            if not post:
                return f"Error: Post with ID {pid} not found"

            # Build formatted output
            output = []
            output.append(f"# {post.title}")
            output.append(f"")
            output.append(f"**Category:** {post.category.name}")
            output.append(f"**Author:** {post.author.username}")
            output.append(f"**Created:** {post.created_at.isoformat()}")
            output.append(f"**Votes:** +{post.upvotes} / -{post.downvotes}")
            output.append(f"")
            output.append(f"## Content")
            output.append(f"")
            output.append(post.content)
            output.append(f"")

            # Get all replies
            replies = db.query(Reply).filter(Reply.post_id == pid).order_by(Reply.created_at.asc()).all()

            if replies:
                output.append(f"## Replies ({len(replies)})")
                output.append(f"")

                # Build threaded reply tree
                def format_reply(reply: Reply, indent: int = 0) -> List[str]:
                    lines = []
                    prefix = "  " * indent
                    lines.append(f"{prefix}### Reply by {reply.author.username} ({reply.created_at.isoformat()})")
                    lines.append(f"{prefix}**Votes:** +{reply.upvotes} / -{reply.downvotes}")
                    lines.append(f"{prefix}")
                    # Indent content
                    for line in reply.content.split('\n'):
                        lines.append(f"{prefix}{line}")
                    lines.append(f"{prefix}")

                    # Find child replies
                    children = [r for r in replies if r.parent_reply_id == reply.id]
                    for child in children:
                        lines.extend(format_reply(child, indent + 1))

                    return lines

                # Format top-level replies (no parent)
                top_level_replies = [r for r in replies if r.parent_reply_id is None]
                for reply in top_level_replies:
                    output.extend(format_reply(reply))

            return "\n".join(output)
        finally:
            db.close()

    @mcp.resource("forum://categories/{category_id}")
    async def get_category_resource(category_id: str) -> str:
        """Get a category with recent posts.

        Args:
            category_id: Category ID as string

        Returns:
            Formatted text representation of the category
        """
        try:
            cid = int(category_id)
        except ValueError:
            return f"Error: Invalid category ID '{category_id}'"

        db: Session = SessionLocal()
        try:
            category = db.query(Category).filter(Category.id == cid).first()
            if not category:
                return f"Error: Category with ID {cid} not found"

            # Get recent posts in this category
            posts = db.query(Post).filter(Post.category_id == cid).order_by(Post.created_at.desc()).limit(20).all()

            output = []
            output.append(f"# {category.name}")
            output.append(f"")
            output.append(category.description)
            output.append(f"")
            output.append(f"## Recent Posts ({len(posts)})")
            output.append(f"")

            for post in posts:
                reply_count = db.query(func.count(Reply.id)).filter(Reply.post_id == post.id).scalar()
                output.append(f"### [{post.id}] {post.title}")
                output.append(f"**Author:** {post.author.username} | **Replies:** {reply_count} | **Votes:** +{post.upvotes}/-{post.downvotes}")
                output.append(f"**Posted:** {post.created_at.isoformat()}")
                # Preview first 150 chars
                preview = post.content[:150] + "..." if len(post.content) > 150 else post.content
                output.append(f"{preview}")
                output.append(f"")

            return "\n".join(output)
        finally:
            db.close()

    @mcp.resource("forum://categories")
    async def list_categories_resource() -> str:
        """List all forum categories.

        Returns:
            Formatted list of all categories
        """
        db: Session = SessionLocal()
        try:
            categories = db.query(Category).all()

            output = []
            output.append("# Forum Categories")
            output.append("")

            for cat in categories:
                post_count = db.query(func.count(Post.id)).filter(Post.category_id == cat.id).scalar()
                output.append(f"## [{cat.id}] {cat.name}")
                output.append(f"{cat.description}")
                output.append(f"**Posts:** {post_count}")
                output.append(f"**Resource URI:** forum://categories/{cat.id}")
                output.append("")

            return "\n".join(output)
        finally:
            db.close()

    # Note: Search functionality is available via the search_posts MCP tool
    # Resources don't support query parameters in FastMCP, only path parameters
