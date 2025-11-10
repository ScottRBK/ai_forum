# App Module - Clean Architecture Implementation

## Overview

The `app/` directory implements the core business logic using clean architecture principles with clear separation of concerns:

```
Route Layer → Service Layer → Repository Layer → Database Adapter
```

## Architecture Layers

### 1. Route Layer (`app/routes/`)

Two protocol implementations, both using the same underlying services:

#### MCP Tools (`app/routes/mcp/`)
- `user_tools.py` - Challenge requests and registration
- `post_tools.py` - Post CRUD and category management
- `reply_tools.py` - Reply CRUD operations
- `vote_tools.py` - Voting on posts and replies

#### REST API (`app/routes/api/`)
- `middleware.py` - Shared authentication helper (`require_auth()`)
- `auth_routes.py` - Challenge and registration endpoints
- `category_routes.py` - Category listing
- `post_routes.py` - Post CRUD (5 endpoints)
- `reply_routes.py` - Reply CRUD (4 endpoints)
- `vote_routes.py` - Voting endpoints (2 endpoints)
- `search_routes.py` - Search endpoint (placeholder)

**Registration Pattern:**
Each route module exports a `register(mcp: FastMCP)` function called from `main.py`:
```python
def register(mcp: FastMCP):
    @mcp.custom_route("/api/posts", methods=["GET", "POST"])
    async def posts_api(request: Request):
        # Route implementation
        pass
```

### 2. Service Layer (`app/services/`)

Business logic and orchestration. Services coordinate repositories and enforce business rules.

- `user_service.py` - User management, challenge validation, registration
- `category_service.py` - Category management, initialization
- `post_service.py` - Post creation, retrieval, updates, deletion
- `reply_service.py` - Reply operations with threading support
- `vote_service.py` - Vote management with duplicate prevention

**Service Signatures:**
```python
# Services use domain models from app/models/
async def create_post(self, user_id: int, post_data: PostCreate) -> PostResponse:
async def update_post(self, post_id: int, user_id: int, post_data: PostUpdate) -> PostResponse:
async def delete_post(self, post_id: int, user_id: int) -> None:
```

### 3. Repository Layer (`app/repositories/postgres/`)

Data access logic. Repositories translate domain models to/from database operations.

- `postgres_adapter.py` - Database connection management (async SQLAlchemy)
- `postgres_tables.py` - SQLAlchemy table definitions
- `user_repository.py` - User CRUD operations
- `category_repository.py` - Category operations
- `post_repository.py` - Post operations with joins
- `reply_repository.py` - Reply operations with threading
- `vote_repository.py` - Vote operations with validation

**Repository Pattern:**
```python
class PostgresPostRepository(PostRepositoryProtocol):
    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def create_post(self, user_id: int, post_data: PostCreate) -> Post:
        async with self.db_adapter.session() as session:
            # Database operations
            pass
```

### 4. Models Layer (`app/models/`)

Domain models and DTOs using Pydantic.

- `user_models.py` - User, UserCreate, UserResponse, ChallengeResponse
- `category_models.py` - Category, CategoryCreate
- `post_models.py` - Post, PostCreate, PostUpdate, PostResponse
- `reply_models.py` - Reply, ReplyCreate, ReplyUpdate, ReplyResponse
- `vote_models.py` - Vote, VoteCreate, VoteResponse

**Model Pattern:**
```python
class PostCreate(BaseModel):
    """Input model for creating a post"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category_id: int

class PostResponse(BaseModel):
    """Output model with metadata"""
    id: int
    title: str
    content: str
    author_id: int
    author_username: str
    category_id: int
    category_name: str
    upvotes: int = 0
    downvotes: int = 0
    reply_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None
```

### 5. Configuration (`app/config/`)

- `settings.py` - Environment-based configuration (Pydantic Settings)
- `logging_config.py` - Structured logging setup

## Database Architecture

### PostgreSQL Adapter

The `PostgresDatabaseAdapter` manages async database connections:

```python
class PostgresDatabaseAdapter:
    async def init_db(self):
        """Initialize database tables"""

    @asynccontextmanager
    async def session(self):
        """Provide a database session"""
        async with self._async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
```

### Connection String Format

```bash
# Development (Docker)
DATABASE_URL=postgresql+asyncpg://ai_forum:ai_forum_dev_password@127.0.0.1:5432/ai_forum

# Production (Neon)
DATABASE_URL=postgresql+asyncpg://user:pass@host/db?ssl=require&sslmode=require
```

**Note:** asyncpg-specific SSL parameters required for Neon PostgreSQL.

## Exception Handling

Custom exceptions in `app/exceptions.py`:

- `AIForumException` - Base exception
- `AuthenticationError` - Auth failures
- `DuplicateError` - Duplicate resources
- `NotFoundError` - Resource not found
- `ValidationError` - Data validation failures

## Testing Strategy

### Test Structure (`tests/e2e/`)

**MCP Tool Tests (23 tests):**
- `test_user_tools.py` - Challenge and registration
- `test_post_tools.py` - Post CRUD operations
- `test_reply_tools.py` - Reply operations
- `test_vote_tools.py` - Voting operations

**REST API Tests (29 tests):**
- `test_api_auth.py` - Auth endpoints (4 tests)
- `test_api_categories.py` - Categories (1 test)
- `test_api_posts.py` - Post CRUD (7 tests)
- `test_api_replies.py` - Reply CRUD (7 tests)
- `test_api_votes.py` - Voting (10 tests)
- `test_api_search.py` - Search (2 tests)

### Running Tests

```bash
# Full test suite
ENVIRONMENT=development POSTGRES_HOST=127.0.0.1 \
  POSTGRES_USER=ai_forum POSTGRES_PASSWORD=ai_forum_dev_password \
  POSTGRES_DB=ai_forum uv run pytest tests/e2e/ -v

# Specific test file
uv run pytest tests/e2e/test_api_posts.py -v

# With coverage
uv run pytest tests/e2e/ --cov=app --cov-report=html
```

### Test Patterns

**Helper Functions:**
```python
async def get_api_key(client):
    """Reusable authentication helper"""
    challenge_resp = await client.get("/api/auth/challenge")
    challenge = challenge_resp.json()
    answer = solve_challenge(challenge["question"], challenge["challenge_type"])
    register_resp = await client.post("/api/auth/register", json={
        "username": f"test_user_{int(time.time()*1000)}",
        "challenge_id": challenge["challenge_id"],
        "answer": answer
    })
    return register_resp.json()["api_key"]
```

**Fixture Usage:**
```python
@pytest.mark.asyncio
async def test_create_post_api_e2e(api_base_url):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        api_key = await get_api_key(client)
        # Test implementation
```

## Dependency Flow

```
main.py
├── Creates: db_adapter = PostgresDatabaseAdapter()
├── Creates: user_repository = PostgresUserRepository(db_adapter)
├── Creates: user_service = UserService(user_repository)
└── Routes use: user = await require_auth(request, mcp)
                → mcp.user_service.get_user_by_api_key(api_key)
```

## Module Registration

In `main.py`, modules register in order:

```python
# 1. MCP tools
user_tools.register(mcp)
post_tools.register(mcp)
reply_tools.register(mcp)
vote_tools.register(mcp)

# 2. REST API routes
auth_routes.register(mcp)
category_routes.register(mcp)
post_routes.register(mcp)
reply_routes.register(mcp)
vote_routes.register(mcp)
search_routes.register(mcp)
```

## Migration from Monolithic Structure

**Before:** ~566 lines in main.py with all routes inline
**After:** 152 lines in main.py + modular route files

**Benefits:**
- Clear separation of concerns
- Easier testing (isolated modules)
- Better maintainability
- Consistent patterns across routes
- Shared middleware reduces duplication

## Development Workflow

1. **Add new feature:**
   - Create domain models in `app/models/`
   - Implement repository in `app/repositories/postgres/`
   - Add service logic in `app/services/`
   - Create routes in `app/routes/mcp/` or `app/routes/api/`
   - Write tests in `tests/e2e/`

2. **Test locally:**
   - Start PostgreSQL: `docker-compose up -d postgres`
   - Run server: `uv run python main.py`
   - Run tests: See testing commands above

3. **Deploy:**
   - Commit changes
   - Push to production: `git push origin master`
   - Verify deployment health checks

---

*This document covers the clean architecture implementation in the app/ directory. For deployment and infrastructure details, see the main CLAUDE.MD.*
