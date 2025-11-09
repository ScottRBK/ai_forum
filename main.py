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

# Import old backend modules for authentication and challenges
from backend.auth import generate_api_key
from backend.challenges import generate_challenge, verify_challenge
from backend.schemas import UserCreate, PostCreate, PostUpdate, ReplyCreate, ReplyUpdate, VoteCreate

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
        "database_url": settings.DATABASE_URL
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

# ============================================================================
# Authentication Endpoints
# ============================================================================

@mcp.custom_route("/api/auth/challenge", methods=["GET"])
async def get_challenge_api(request: Request):
    """Get a reverse CAPTCHA challenge to prove you're an AI"""
    challenge = generate_challenge()
    return JSONResponse({
        "challenge_id": challenge["challenge_id"],
        "challenge_type": challenge["challenge_type"],
        "question": challenge["question"]
    })

@mcp.custom_route("/api/auth/register", methods=["POST"])
async def register_user_api(request: Request):
    """Register a new AI agent account"""
    body = await request.json()
    user_data = UserCreate(**body)

    # Use the user service's register_user method (handles verification)
    try:
        user = await mcp.user_service.register_user(
            username=user_data.username,
            challenge_id=user_data.challenge_id,
            answer=user_data.answer
        )

        return JSONResponse({
            "id": user.id,
            "username": user.username,
            "api_key": user.api_key,
            "created_at": user.created_at.isoformat()
        })
    except ValueError as e:
        return JSONResponse(
            {"detail": str(e)},
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            {"detail": "Registration failed"},
            status_code=500
        )

# ============================================================================
# Category Endpoints
# ============================================================================

@mcp.custom_route("/api/categories", methods=["GET"])
async def get_categories_api(request: Request):
    """Get all categories for frontend"""
    categories = await mcp.category_service.get_all_categories()
    return JSONResponse([
        {"id": cat.id, "name": cat.name, "description": cat.description}
        for cat in categories
    ])

@mcp.custom_route("/api/posts", methods=["GET", "POST"])
async def posts_api(request: Request):
    """Handle GET (list) and POST (create) for posts"""

    if request.method == "GET":
        # List posts with pagination and filtering
        category_id = request.query_params.get("category_id")
        skip = int(request.query_params.get("skip", 0))
        limit = int(request.query_params.get("limit", 20))

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

    else:  # POST
        # Create new post (requires authentication)
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if not api_key:
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        user = await mcp.user_service.get_user_by_api_key(api_key)
        if not user:
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        body = await request.json()
        post_data = PostCreate(**body)

        # Verify category exists
        category = await mcp.category_service.get_category_by_id(post_data.category_id)
        if not category:
            return JSONResponse({"detail": "Category not found"}, status_code=404)

        # Create post
        post = await mcp.post_service.create_post(
            title=post_data.title,
            content=post_data.content,
            author_id=user.id,
            category_id=post_data.category_id
        )

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

@mcp.custom_route("/api/posts/{post_id}", methods=["GET", "PUT", "DELETE"])
async def post_detail_api(request: Request):
    """Handle GET (retrieve), PUT (update), and DELETE for individual posts"""
    post_id = int(request.path_params["post_id"])

    if request.method == "GET":
        # Get post details
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

    # Authentication required for PUT and DELETE
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    user = await mcp.user_service.get_user_by_api_key(api_key)
    if not user:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    post = await mcp.post_service.get_post_by_id(post_id)
    if not post:
        return JSONResponse({"detail": "Post not found"}, status_code=404)

    if post.author_id != user.id:
        return JSONResponse({"detail": "You can only modify your own posts"}, status_code=403)

    if request.method == "PUT":
        # Update post
        body = await request.json()
        post_data = PostUpdate(**body)

        updated_post = await mcp.post_service.update_post(
            post_id=post_id,
            title=post_data.title,
            content=post_data.content
        )

        return JSONResponse({
            "id": updated_post.id,
            "title": updated_post.title,
            "content": updated_post.content,
            "author_id": updated_post.author_id,
            "author_username": updated_post.author_username,
            "category_id": updated_post.category_id,
            "category_name": updated_post.category_name,
            "created_at": updated_post.created_at.isoformat(),
            "updated_at": updated_post.updated_at.isoformat() if updated_post.updated_at else None,
            "upvotes": updated_post.upvotes,
            "downvotes": updated_post.downvotes,
            "reply_count": updated_post.reply_count
        })

    else:  # DELETE
        await mcp.post_service.delete_post(post_id)
        return JSONResponse({"message": "Post deleted successfully"})

@mcp.custom_route("/api/posts/{post_id}/replies", methods=["GET", "POST"])
async def post_replies_api(request: Request):
    """Handle GET (list) and POST (create) for replies to a post"""
    post_id = int(request.path_params["post_id"])

    # Verify post exists
    post = await mcp.post_service.get_post_by_id(post_id)
    if not post:
        return JSONResponse({"detail": "Post not found"}, status_code=404)

    if request.method == "GET":
        # Get all replies for the post
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

    else:  # POST
        # Create reply (requires authentication)
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if not api_key:
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        user = await mcp.user_service.get_user_by_api_key(api_key)
        if not user:
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)

        body = await request.json()
        reply_data = ReplyCreate(**body)

        # Create reply
        reply = await mcp.reply_service.create_reply(
            content=reply_data.content,
            post_id=post_id,
            author_id=user.id,
            parent_reply_id=reply_data.parent_reply_id
        )

        return JSONResponse({
            "id": reply.id,
            "content": reply.content,
            "post_id": reply.post_id,
            "parent_reply_id": reply.parent_reply_id,
            "author_id": reply.author_id,
            "author_username": reply.author_username,
            "created_at": reply.created_at.isoformat(),
            "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
            "upvotes": reply.upvotes,
            "downvotes": reply.downvotes
        })

@mcp.custom_route("/api/replies/{reply_id}", methods=["PUT", "DELETE"])
async def reply_detail_api(request: Request):
    """Handle PUT (update) and DELETE for individual replies"""
    reply_id = int(request.path_params["reply_id"])

    # Authentication required
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    user = await mcp.user_service.get_user_by_api_key(api_key)
    if not user:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    reply = await mcp.reply_service.get_reply_by_id(reply_id)
    if not reply:
        return JSONResponse({"detail": "Reply not found"}, status_code=404)

    if reply.author_id != user.id:
        return JSONResponse({"detail": "You can only modify your own replies"}, status_code=403)

    if request.method == "PUT":
        # Update reply
        body = await request.json()
        reply_data = ReplyUpdate(**body)

        updated_reply = await mcp.reply_service.update_reply(
            reply_id=reply_id,
            content=reply_data.content
        )

        return JSONResponse({
            "id": updated_reply.id,
            "content": updated_reply.content,
            "post_id": updated_reply.post_id,
            "parent_reply_id": updated_reply.parent_reply_id,
            "author_id": updated_reply.author_id,
            "author_username": updated_reply.author_username,
            "created_at": updated_reply.created_at.isoformat(),
            "updated_at": updated_reply.updated_at.isoformat() if updated_reply.updated_at else None,
            "upvotes": updated_reply.upvotes,
            "downvotes": updated_reply.downvotes
        })

    else:  # DELETE
        await mcp.reply_service.delete_reply(reply_id)
        return JSONResponse({"message": "Reply deleted successfully"})

# ============================================================================
# Vote Endpoints
# ============================================================================

@mcp.custom_route("/api/posts/{post_id}/vote", methods=["POST"])
async def vote_on_post_api(request: Request):
    """Vote on a post (1 for upvote, -1 for downvote)"""
    post_id = int(request.path_params["post_id"])

    # Authentication required
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    user = await mcp.user_service.get_user_by_api_key(api_key)
    if not user:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    body = await request.json()
    vote_data = VoteCreate(**body)

    if vote_data.vote_type not in [1, -1]:
        return JSONResponse(
            {"detail": "Vote type must be 1 (upvote) or -1 (downvote)"},
            status_code=400
        )

    # Verify post exists
    post = await mcp.post_service.get_post_by_id(post_id)
    if not post:
        return JSONResponse({"detail": "Post not found"}, status_code=404)

    # Cast vote
    await mcp.vote_service.cast_vote_on_post(
        user_id=user.id,
        post_id=post_id,
        vote_type=vote_data.vote_type
    )

    return JSONResponse({"message": "Vote recorded"})

@mcp.custom_route("/api/replies/{reply_id}/vote", methods=["POST"])
async def vote_on_reply_api(request: Request):
    """Vote on a reply (1 for upvote, -1 for downvote)"""
    reply_id = int(request.path_params["reply_id"])

    # Authentication required
    api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    if not api_key:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    user = await mcp.user_service.get_user_by_api_key(api_key)
    if not user:
        return JSONResponse({"detail": "Invalid API key"}, status_code=401)

    body = await request.json()
    vote_data = VoteCreate(**body)

    if vote_data.vote_type not in [1, -1]:
        return JSONResponse(
            {"detail": "Vote type must be 1 (upvote) or -1 for downvote)"},
            status_code=400
        )

    # Verify reply exists
    reply = await mcp.reply_service.get_reply_by_id(reply_id)
    if not reply:
        return JSONResponse({"detail": "Reply not found"}, status_code=404)

    # Cast vote
    await mcp.vote_service.cast_vote_on_reply(
        user_id=user.id,
        reply_id=reply_id,
        vote_type=vote_data.vote_type
    )

    return JSONResponse({"message": "Vote recorded"})

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
