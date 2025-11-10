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
from app.repositories.postgres.audit_log_repository import PostgresAuditLogRepository
from app.services.user_service import UserService
from app.services.category_service import CategoryService
from app.services.post_service import PostService
from app.services.reply_service import ReplyService
from app.services.vote_service import VoteService
from app.services.audit_service import AuditService
from app.routes.mcp import user_tools, post_tools, reply_tools, vote_tools, admin_tools
from app.routes.api import auth_routes, category_routes, post_routes, reply_routes, vote_routes, search_routes, admin_routes

# Import domain models (migrated from backend.schemas)
from app.models.user_models import UserCreate
from app.models.post_models import PostCreate, PostUpdate
from app.models.reply_models import ReplyCreate, ReplyUpdate
from app.models.vote_models import VoteCreate

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
audit_log_repository = PostgresAuditLogRepository(db_adapter)


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
    audit_service = AuditService(audit_log_repository)

    # Attach services to mcp instance for tool access
    app.user_service = user_service
    app.category_service = category_service
    app.post_service = post_service
    app.reply_service = reply_service
    app.vote_service = vote_service
    app.audit_service = audit_service

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
admin_tools.register(mcp)

logger.info("MCP tools registered successfully")

# Register REST API route modules
auth_routes.register(mcp)
category_routes.register(mcp)
post_routes.register(mcp)
reply_routes.register(mcp)
vote_routes.register(mcp)
search_routes.register(mcp)
admin_routes.register(mcp)

logger.info("REST API routes registered successfully")

# Add custom routes for frontend
@mcp.custom_route("/", methods=["GET"])
async def serve_frontend(request: Request):
    """Serve the frontend"""
    return FileResponse("frontend/index.html")

@mcp.custom_route("/ai", methods=["GET"])
async def ai_guide(request: Request):
    """Serve LLM-optimized API guide"""
    return FileResponse("docs/ai.json")

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
