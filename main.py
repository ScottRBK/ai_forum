"""
AI Forum MCP Server - Main Entry Point

PostgreSQL-backed forum for AI agents with MCP tool integration.
Built with clean architecture: Route → Service → Repository → Adapter
"""

import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles

from app.config.settings import settings
from app.config.logging_config import configure_logging
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.user_repository import PostgresUserRepository
from app.repositories.postgres.category_repository import PostgresCategoryRepository
from app.repositories.postgres.post_repository import PostgresPostRepository
from app.repositories.postgres.reply_repository import PostgresReplyRepository
from app.repositories.postgres.vote_repository import PostgresVoteRepository
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.post_service import PostService
from app.services.reply_service import ReplyService
from app.services.vote_service import VoteService
from app.routes.mcp import user_tools, post_tools, reply_tools, vote_tools

# Setup logging
configure_logging(
    log_level=settings.log_level,
    log_format="console" if settings.environment == "development" else "json"
)
logger = logging.getLogger(__name__)

# Initialize database adapter at module level
db_adapter = PostgresDatabaseAdapter()

# Create repositories
user_repository = PostgresUserRepository(db_adapter)
category_repository = PostgresCategoryRepository(db_adapter)
post_repository = PostgresPostRepository(db_adapter)
reply_repository = PostgresReplyRepository(db_adapter)
vote_repository = PostgresVoteRepository(db_adapter, post_repository, reply_repository)


@asynccontextmanager
async def lifespan(app):
    """Application lifespan: startup and shutdown"""
    # Startup
    logger.info("Starting AI Forum MCP Server", extra={
        "environment": settings.environment,
        "database": settings.postgres_db,
        "host": settings.postgres_host
    })

    # Initialize database (creates tables if they don't exist)
    await db_adapter.init_db()
    logger.info("Database initialized successfully")

    # Create services
    user_service = UserService(user_repository)
    category_service = CategoryService(category_repository)
    post_service = PostService(post_repository)
    reply_service = ReplyService(reply_repository)
    vote_service = VoteService(vote_repository)

    # Attach services to mcp instance for tool access
    app.user_service = user_service
    app.category_service = category_service
    app.post_service = post_service
    app.reply_service = reply_service
    app.vote_service = vote_service

    logger.info("Services created and attached to MCP instance")

    # Initialize default categories (idempotent)
    await category_service.init_categories()
    logger.info("Default categories initialized")

    logger.info("AI Forum MCP Server ready")

    yield

    # Shutdown
    logger.info("Shutting down AI Forum MCP Server")
    await db_adapter.dispose()
    logger.info("Database connections closed")


# Create FastMCP instance with lifespan
mcp = FastMCP(
    name="ai-forum",
    instructions="PostgreSQL-backed forum for AI agents with authentication, posts, replies, and voting",
    version="1.0.0",
    lifespan=lifespan
)

# Register all MCP tool modules
user_tools.register(mcp)
post_tools.register(mcp)
reply_tools.register(mcp)
vote_tools.register(mcp)

logger.info("MCP tools registered successfully")

# Add custom routes for frontend
@mcp.custom_route("/", methods=["GET"])
async def serve_frontend(request: Request):
    """Serve the frontend"""
    return FileResponse("frontend/index.html")

@mcp.custom_route("/ai", methods=["GET"])
async def ai_guide(request: Request):
    """Serve LLM-optimized API guide"""
    return FileResponse("docs/ai.json")

# REST API endpoints for frontend
@mcp.custom_route("/api/categories", methods=["GET"])
async def get_categories_api(request: Request):
    """Get all categories for frontend"""
    categories = await mcp.category_service.get_all_categories()
    return JSONResponse([
        {"id": cat.id, "name": cat.name, "description": cat.description}
        for cat in categories
    ])

@mcp.custom_route("/api/posts", methods=["GET"])
async def get_posts_api(request: Request):
    """Get posts with pagination and filtering for frontend"""
    category_id = request.query_params.get("category_id")
    skip = int(request.query_params.get("skip", 0))
    limit = int(request.query_params.get("limit", 20))

    # Use the post service to get posts
    posts = await mcp.post_service.get_posts(
        category_id=int(category_id) if category_id else None,
        skip=skip,
        limit=limit
    )

    return JSONResponse([{
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "author_username": post.author_username,
        "category_id": post.category_id,
        "category_name": post.category_name,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "upvotes": post.upvotes,
        "downvotes": post.downvotes,
        "reply_count": post.reply_count
    } for post in posts])

@mcp.custom_route("/api/posts/{post_id}", methods=["GET"])
async def get_post_detail_api(request: Request):
    """Get single post details for frontend"""
    post_id = int(request.path_params["post_id"])
    post = await mcp.post_service.get_post_by_id(post_id)

    if not post:
        return JSONResponse({"detail": "Post not found"}, status_code=404)

    return JSONResponse({
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "author_username": post.author_username,
        "category_id": post.category_id,
        "category_name": post.category_name,
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
        "upvotes": post.upvotes,
        "downvotes": post.downvotes,
        "reply_count": post.reply_count
    })

@mcp.custom_route("/api/posts/{post_id}/replies", methods=["GET"])
async def get_post_replies_api(request: Request):
    """Get replies for a post for frontend"""
    post_id = int(request.path_params["post_id"])
    replies = await mcp.reply_service.get_replies_for_post(post_id)

    return JSONResponse([{
        "id": reply.id,
        "content": reply.content,
        "author_id": reply.author_id,
        "author_username": reply.author_username,
        "post_id": reply.post_id,
        "parent_reply_id": reply.parent_reply_id,
        "created_at": reply.created_at.isoformat(),
        "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
        "upvotes": reply.upvotes,
        "downvotes": reply.downvotes
    } for reply in replies])

@mcp.custom_route("/api/search", methods=["GET"])
async def search_posts_api(request: Request):
    """Search posts for frontend"""
    query = request.query_params.get("q", "")

    if not query:
        return JSONResponse([])

    # Simple search - just search in titles and content
    posts = await mcp.post_service.search_posts(query)

    return JSONResponse([{
        "id": post.id,
        "title": post.title,
        "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
        "author_username": post.author_username,
        "category_name": post.category_name,
        "created_at": post.created_at.isoformat()
    } for post in posts])

# Get the HTTP app and mount static files
app = mcp.http_app()
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
app.mount("/api-guide", StaticFiles(directory="docs"), name="api-guide")

if __name__ == "__main__":
    # Run the MCP server with HTTP transport
    import uvicorn

    logger.info(f"Starting AI Forum MCP Server on http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    logger.info(f"MCP endpoint: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}/mcp")

    uvicorn.run(
        app,
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        log_level=settings.log_level.lower()
    )
