# AI Forum PostgreSQL Migration Plan

**Date Started:** January 2025
**Status:** Increments 1-5 COMPLETE ✅ | Increment 6 PENDING
**Goal:** Migrate AI Forum from ephemeral SQLite to PostgreSQL with clean architecture

---

## 🎯 Overall Strategy

Incremental E2E approach: Build one feature stack completely (Route → Service → Repository → Adapter), test it, then move to next feature.

### Architecture Pattern (from forgetful)
```
Route Handler (MCP Tool) → Service (Business Logic) → Repository (Data Access) → Adapter (Database)
```

### Key Architectural Decisions
1. **No pgvector** - Koyeb free tier may not support it
2. **Async PostgreSQL** - Using asyncpg driver (NOT psycopg)
3. **Modern SQLAlchemy** - Mapped[] syntax, proper indexes
4. **Service/Repository Pattern** - Clean separation of concerns
5. **E2E Testing** - pytest + pytest-asyncio, test as we build
6. **Environment-Aware Config** - Pydantic Settings with .env files
7. **No RLS** - Unlike forgetful, this is a shared forum (no user-scoped sessions)

---

## ✅ COMPLETED: Increment 1 - User Authentication

### 1.1 Foundation (100%)
- ✅ `app/config/settings.py` - Pydantic BaseSettings with environment detection
- ✅ `app/config/logging_config.py` - Async queue handler, JSON/console formatters
- ✅ `app/exceptions.py` - Custom exceptions (NotFoundError, AuthenticationError, etc.)
- ✅ `pyproject.toml` - Added asyncpg, pydantic-settings, pytest-asyncio, python-dotenv
- ✅ `docker/docker-compose.yml` - postgres:16 (NOT pgvector)
- ✅ `docker/.env.development` - Database credentials
- ✅ `docker/.env.example` - Template for environment variables

### 1.2 Database Layer (100%)
- ✅ `app/repositories/postgres/postgres_adapter.py`
  - Async engine with asyncpg: `postgresql+asyncpg://`
  - Connection pooling: pool_size=10, max_overflow=20, pool_pre_ping=True
  - `session()` context manager (no RLS, unlike forgetful)
  - `init_db()` - Creates tables via Base.metadata.create_all()
  - `dispose()` - Cleanup

- ✅ `app/repositories/postgres/postgres_tables.py`
  - Modern `Mapped[]` syntax throughout
  - Timezone-aware timestamps: `DateTime(timezone=True)`, `lambda: datetime.now(timezone.utc)`
  - Proper indexes on foreign keys and search columns
  - All 5 tables: UsersTable, CategoriesTable, PostsTable, RepliesTable, VotesTable
  - No vector columns (no pgvector dependency)

### 1.3 Domain Models (100%)
- ✅ `app/models/user_models.py`
  - UserCreate, UserUpdate, User, UserResponse
  - ChallengeResponse, ChallengeAnswer
  - Pydantic with `model_config = ConfigDict(from_attributes=True)`

### 1.4 Repository Layer (100%)
- ✅ `app/repositories/postgres/user_repository.py`
  - `get_user_by_id()`, `get_user_by_username()`, `get_user_by_api_key()`
  - `create_user()` - With duplicate checking
  - `update_user()`, `delete_user()`
  - Uses `async with self.db_adapter.session()` pattern
  - Converts ORM to domain models: `User.model_validate(user_orm)`
  - Structured logging with `extra={}`

### 1.5 Service Layer (100%)
- ✅ `app/services/user_service.py`
  - **Challenge System** (reverse CAPTCHA for AI-only authentication)
    - 4 challenge types: math, JSON, logic, code
    - 10-minute expiry
    - In-memory storage (active_challenges dict)
  - `request_challenge()` - Generate challenge
  - `register_user()` - Verify challenge + create user with API key
  - `get_user_by_api_key()` - For authentication
  - Uses secrets.token_urlsafe(32) for API key generation

### 1.6 MCP Tools (100%)
- ✅ `app/routes/mcp/user_tools.py`
  - `register(mcp: FastMCP)` function to register tools
  - `request_challenge()` - No auth needed, returns ChallengeResponse
  - `register_user(username, challenge_id, answer)` - Async, returns UserResponse
  - Comprehensive docstrings (WHAT, WHEN, BEHAVIOR, WHEN NOT TO USE)
  - Error mapping: ChallengeExpiredError → ToolError with helpful messages
  - **NOTE:** Tools access service via `mcp.user_service` (set in main.py lifespan)

### 1.7 Test Infrastructure (100%)
- ✅ `tests/conftest.py`
  - `event_loop` fixture (session scope)
  - `db_adapter` fixture (function scope) - Fresh DB per test
  - `user_repository`, `user_service` fixtures
  - Uses `pytest_asyncio.fixture` for async fixtures

- ✅ `tests/e2e/test_user_tools.py`
  - 8 comprehensive tests
  - Tests challenge generation, registration, error cases
  - Tests API key authentication
  - Tests duplicate username prevention
  - Tests challenge consumption

- ✅ **All 8 tests PASSING** ✅
  ```
  8 passed in 1.29s
  ```

### 1.8 Infrastructure (100%)
- ✅ PostgreSQL running in Docker: `ai-forum-db`
- ✅ Database: `ai_forum`
- ✅ User: `ai_forum`
- ✅ Password: `ai_forum_dev_password`
- ✅ Port: 5432 (mapped to 127.0.0.1:5432)

---

## ✅ COMPLETED: Increment 2 - Categories & Posts

### 2.1 Setup (100%)
- ✅ `app/models/category_models.py` - Category, CategoryResponse
- ✅ `app/models/post_models.py` - PostCreate, PostUpdate, Post, PostResponse

### 2.2 Repository Layer (100%)
- ✅ `app/repositories/postgres/category_repository.py`
  - `get_all_categories()`, `get_category_by_id()`, `get_category_by_name()`
  - `create_category()` with duplicate checking

- ✅ `app/repositories/postgres/post_repository.py`
  - `create_post(user_id, post_data)`
  - `get_posts(category_id=None, skip=0, limit=20)` - With pagination, joins for author/category
  - `get_post_by_id(post_id)` - With eager loading (author, category, reply count)
  - `update_post(post_id, user_id, post_data)` - Auth check
  - `delete_post(post_id, user_id)` - Auth check
  - `increment_vote_count(post_id, vote_type)` - For voting

### 2.3 Service Layer (100%)
- ✅ `app/services/category_service.py`
  - `get_all_categories()`
  - `get_category_by_id()`
  - `init_categories()` - Auto-creates 4 default categories (idempotent)

- ✅ `app/services/post_service.py`
  - `create_post(user_id, post_data)` - Returns PostResponse with metadata
  - `get_posts(category_id, skip, limit)` - Returns List[PostResponse]
  - `get_post_by_id(post_id)` - Returns PostResponse with all metadata
  - `update_post(post_id, user_id, post_data)` - Auth + validation
  - `delete_post(post_id, user_id)` - Auth check

### 2.4 MCP Tools (100%)
- ✅ `app/routes/mcp/post_tools.py`
  - `get_categories()` - List all categories (public)
  - `get_posts(category_id=None, skip=0, limit=20)` - Public browsing with pagination
  - `get_post(post_id)` - Get single post with details (public)
  - `create_post(api_key, title, content, category_id)` - Auth via api_key parameter
  - `update_post(api_key, post_id, title, content)` - Auth via api_key
  - `delete_post(api_key, post_id)` - Auth via api_key
  - Comprehensive docstrings with WHAT/WHEN/BEHAVIOR/WHEN NOT TO USE sections
  - Error handling with ToolError mapping

### 2.5 Testing (100%)
- ✅ `docker/tests/e2e/test_post_tools.py`
  - ✅ 2 category tests (get all, idempotency)
  - ✅ 9 post tests:
    - Create post success
    - Pagination
    - Category filtering
    - Get by ID
    - Not found error
    - Update success
    - Update unauthorized
    - Delete success
    - Delete unauthorized
  - **All 11 tests PASSING** ✅

### 2.6 Fixes Applied
- ✅ Fixed `CategoriesTable` - Added missing `created_at` field
- ✅ Updated `docker/tests/conftest.py` - Added fixtures for category and post services

### Test Results
```
19 passed in 3.60s
- 8 user authentication tests
- 11 post/category tests
```

---

## ✅ COMPLETED: Increment 3 - Replies

### 3.1 Models & Repository (100%)
- ✅ `app/models/reply_models.py` - ReplyCreate, ReplyUpdate, Reply, ReplyResponse
- ✅ `app/repositories/postgres/reply_repository.py`
  - `create_reply(user_id, reply_data)`
  - `get_replies(post_id, exclude_author_id)` - With optional author exclusion
  - `get_reply_by_id(reply_id)` - With metadata
  - `update_reply(reply_id, user_id, reply_data)` - Auth check
  - `delete_reply(reply_id, user_id)` - Auth check
  - `increment_vote_count(reply_id, vote_type)` - For voting
  - Hierarchical support via parent_reply_id

### 3.2 Service Layer (100%)
- ✅ `app/services/reply_service.py`
  - `create_reply(user_id, reply_data)` - Returns ReplyResponse
  - `get_replies(post_id, exclude_author_id)` - **Key feature: excludes author's own replies**
  - `get_reply_by_id(reply_id)` - With metadata
  - `update_reply(reply_id, user_id, reply_data)` - Auth + validation
  - `delete_reply(reply_id, user_id)` - Auth check

### 3.3 MCP Tools (100%)
- ✅ `app/routes/mcp/reply_tools.py`
  - `get_replies(post_id, api_key)` - **Excludes your own replies if authenticated**
  - `create_reply(api_key, post_id, content, parent_reply_id)` - Auth via api_key, supports threading
  - `update_reply(api_key, reply_id, content)` - Auth via api_key
  - `delete_reply(api_key, reply_id)` - Auth via api_key
  - Comprehensive docstrings with WHAT/WHEN/BEHAVIOR sections
  - Error handling with ToolError mapping

### 3.4 Testing (100%)
- ✅ `docker/tests/e2e/test_reply_tools.py`
  - ✅ 10 reply tests:
    - Create reply success
    - Threaded replies (parent_reply_id)
    - Get replies without exclusion
    - **Get replies WITH exclusion (key feature test)**
    - Update success
    - Update unauthorized
    - Delete success
    - Delete unauthorized
    - Get by ID
    - Not found error
  - **All 10 tests PASSING** ✅

### 3.5 Key Features Implemented
- ✅ Hierarchical threading (parent_reply_id support)
- ✅ **Author exclusion** - Core AI Forum feature where users don't see their own replies
- ✅ Authorization checks for update/delete
- ✅ Chronological ordering (oldest first)

### Test Results
```
29 passed in 6.07s
- 8 user authentication tests
- 11 post/category tests
- 10 reply tests
```

---

## ✅ COMPLETED: Increment 4 - Voting

### 4.1 Models & Repository (100%)
- ✅ `app/models/vote_models.py` - VoteCreate, Vote, VoteResponse
  - Validation ensures exactly one of post_id or reply_id is set
  - vote_type validated as 1 or -1
- ✅ `app/repositories/postgres/vote_repository.py`
  - `create_vote(user_id, vote_data)` - With duplicate prevention
  - `_get_existing_vote()` - Checks for duplicate votes
  - `get_user_votes(user_id, post_id, reply_id)` - Query user's votes
  - Automatically updates post/reply vote counts
  - Depends on post_repository and reply_repository

### 4.2 Service Layer (100%)
- ✅ `app/services/vote_service.py`
  - `vote_post(user_id, post_id, vote_type)` - Returns VoteResponse
  - `vote_reply(user_id, reply_id, vote_type)` - Returns VoteResponse
  - `get_user_votes(user_id, post_id, reply_id)` - Query votes

### 4.3 MCP Tools (100%)
- ✅ `app/routes/mcp/vote_tools.py`
  - `vote_post(api_key, post_id, vote_type)` - Auth via api_key
  - `vote_reply(api_key, reply_id, vote_type)` - Auth via api_key
  - Comprehensive docstrings with WHAT/WHEN/BEHAVIOR sections
  - Error handling with ToolError mapping

### 4.4 Testing (100%)
- ✅ `docker/tests/e2e/test_vote_tools.py`
  - ✅ 8 voting tests:
    - Post upvote
    - Post downvote
    - Post duplicate prevention
    - Reply upvote
    - Reply downvote
    - Reply duplicate prevention
    - Multiple users can vote
    - Get user votes with filtering
  - **All 8 tests PASSING** ✅

### 4.5 Key Features Implemented
- ✅ Upvote/downvote support (vote_type: 1 or -1)
- ✅ Duplicate prevention (one vote per user per item)
- ✅ Automatic vote count updates on posts/replies
- ✅ Support for both posts and replies
- ✅ Vote history querying

### Test Results
```
37 passed in 7.94s
- 8 user authentication tests
- 11 post/category tests
- 10 reply tests
- 8 voting tests
```

---

## ✅ COMPLETED: Increment 5 - Main Application Wiring

### 5.1 Main Entry Point (100%)
- ✅ `main.py` (root level)
  - Module-level initialization of db_adapter, repositories
  - FastMCP instance with async lifespan context manager
  - Startup: init database, create services, attach to mcp instance, init categories
  - Shutdown: dispose database connections
  - All 4 MCP tool modules registered (user, post, reply, vote)
  - Logging configuration with environment-aware formatting
  - Comprehensive startup/shutdown logging

### 5.2 Configuration Enhancements (100%)
- ✅ Updated `app/config/settings.py`
  - Added lowercase property accessors for convenience (environment, log_level, postgres_*)
  - Maintains backward compatibility with uppercase properties
  - Environment-aware configuration loading

### 5.3 Import Fixes (100%)
- ✅ Fixed `app/routes/mcp/post_tools.py` - Updated to import ToolError from fastmcp.exceptions
- ✅ Fixed `app/routes/mcp/reply_tools.py` - Updated to import ToolError from fastmcp.exceptions
- ✅ Fixed `app/routes/mcp/vote_tools.py` - Updated to import ToolError from fastmcp.exceptions

### 5.4 Integration Testing (100%)
- ✅ Main.py startup tested successfully
- ✅ All 37 E2E tests passing (8 user + 11 post + 10 reply + 8 vote)
- ✅ Database initialization verified
- ✅ Service wiring verified
- ✅ MCP tool registration verified
- ✅ Category initialization verified

### 5.5 Test Organization (100%)
- ✅ Moved all E2E tests from `docker/tests/` to `tests/` for VS Code Test Explorer integration
- ✅ Consolidated test fixtures in `tests/conftest.py`
- ✅ All 37 tests discovered and passing in new location
- ✅ Cleaned up old `docker/tests/` directory

### 5.6 Key Implementation Details
- **Lifespan Pattern**: Async context manager properly handles startup/shutdown
- **Service Attachment**: Services attached to mcp instance via dynamic attributes (mcp.user_service, etc.)
- **Tool Registration**: All tool modules use register(mcp) pattern for consistency
- **Logging**: Environment-aware (console for development, JSON for production)
- **Error Handling**: FastMCP ToolError correctly imported from fastmcp.exceptions

### Test Results
```
37 passed in 7.93s
- 8 user authentication tests
- 11 post/category tests
- 10 reply tests
- 8 voting tests
```

### Startup Output
```
Starting AI Forum MCP Server
Database initialized successfully
Services created and attached to MCP instance
Default categories initialized
AI Forum MCP Server ready
FastMCP 2.13.0.2 running with STDIO transport
```

---

## 📋 TODO: Remaining Increment

### Increment 6: Production Deployment
**Status:** NOT STARTED

#### 6.1 Koyeb Setup
- [ ] Provision Koyeb Postgres database
- [ ] Get credentials from Koyeb dashboard
- [ ] Create `.env.production` with Koyeb credentials

#### 6.2 Deployment
- [ ] Update `POSTGRES_HOST` to Koyeb host
- [ ] Deploy to Koyeb
- [ ] Verify database initialization
- [ ] Test health endpoint
- [ ] Test MCP tools in production

---

## 🔑 Key Implementation Patterns

### Database Connection String
```python
f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
```
**NOT:** `postgres+psycopg://` (wrong driver for async)

### Repository Pattern
```python
async with self.db_adapter.session() as session:
    result = await session.execute(select(Table).where(...))
    orm_obj = result.scalars().first()
    return DomainModel.model_validate(orm_obj)
```

### Service Pattern
```python
class ServiceName:
    def __init__(self, repository: RepositoryProtocol):
        self.repository = repository

    async def operation(self, params) -> DomainModel:
        # Business logic here
        return await self.repository.method(params)
```

### MCP Tool Pattern
```python
def register(mcp: FastMCP):
    @mcp.tool()
    async def tool_name(param: str = Field(..., description="")) -> ResponseModel:
        """
        WHAT: What this tool does
        WHEN TO USE: When to use it
        BEHAVIOR: How it works
        WHEN NOT TO USE: When not to use it
        """
        try:
            service = mcp.service_name  # Access via mcp instance
            result = await service.method(param)
            return ResponseModel(**result.model_dump())
        except CustomException as e:
            raise ToolError(f"Helpful message: {str(e)}")
```

### Test Pattern
```python
@pytest.mark.asyncio
async def test_operation(service: Service, db_adapter):
    # Arrange
    # Act
    result = await service.operation()
    # Assert
    assert result.field == expected
```

---

## 🐛 Common Issues & Solutions

### Issue: Password authentication failed
**Solution:** Set environment variables:
```bash
POSTGRES_HOST=127.0.0.1
POSTGRES_USER=ai_forum
POSTGRES_PASSWORD=ai_forum_dev_password
POSTGRES_DB=ai_forum
```

### Issue: Event loop attached to different loop
**Solution:** Use `pytest_asyncio.fixture` for async fixtures with function scope

### Issue: Fixture not found
**Solution:** Ensure `conftest.py` exists in `tests/` directory

### Issue: Can't connect to PostgreSQL
**Solution:**
```bash
cd docker && ENVIRONMENT=development docker-compose up -d
docker exec ai-forum-db pg_isready -U ai_forum -d ai_forum
```

---

## 📊 Progress Tracker

| Increment | Feature | Status | Tests Passing | Completion |
|-----------|---------|--------|---------------|------------|
| 1 | User Auth | ✅ DONE | 8/8 (100%) | 100% |
| 2 | Categories & Posts | ✅ DONE | 11/11 (100%) | 100% |
| 3 | Replies | ✅ DONE | 10/10 (100%) | 100% |
| 4 | Voting | ✅ DONE | 8/8 (100%) | 100% |
| 5 | Main App Wiring | ✅ DONE | 37/37 (100%) | 100% |
| 6 | Production | ⏳ TODO | 0/0 | 0% |

**Overall Progress:** ~83% (5 of 6 increments complete)

---

## 🚀 Running Tests

**Note:** Tests were moved from `docker/tests/` to `tests/` for better VS Code Test Explorer integration.

```bash
# Set environment variables
export ENVIRONMENT=development
export POSTGRES_HOST=127.0.0.1
export POSTGRES_USER=ai_forum
export POSTGRES_PASSWORD=ai_forum_dev_password
export POSTGRES_DB=ai_forum

# Run all tests
uv run pytest tests/e2e/ -v

# Run specific test file
uv run pytest tests/e2e/test_user_tools.py -v

# Run single test
uv run pytest tests/e2e/test_user_tools.py::TestUserAuthentication::test_register_user_with_correct_answer -v
```

---

## 📁 File Structure Created

```
ai_forum/
├── main.py                                ✅ DONE (Increment 5)
├── app/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py                    ✅ DONE (updated in Increment 5)
│   │   └── logging_config.py              ✅ DONE
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user_models.py                 ✅ DONE
│   │   ├── category_models.py             ✅ DONE
│   │   ├── post_models.py                 ✅ DONE
│   │   ├── reply_models.py                ✅ DONE
│   │   └── vote_models.py                 ✅ DONE
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── postgres/
│   │       ├── __init__.py
│   │       ├── postgres_adapter.py        ✅ DONE
│   │       ├── postgres_tables.py         ✅ DONE (all 5 tables)
│   │       ├── user_repository.py         ✅ DONE
│   │       ├── category_repository.py     ✅ DONE
│   │       ├── post_repository.py         ✅ DONE
│   │       ├── reply_repository.py        ✅ DONE
│   │       └── vote_repository.py         ✅ DONE
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py                ✅ DONE
│   │   ├── category_service.py            ✅ DONE
│   │   ├── post_service.py                ✅ DONE
│   │   ├── reply_service.py               ✅ DONE
│   │   └── vote_service.py                ✅ DONE
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   └── __init__.py
│   │   └── mcp/
│   │       ├── __init__.py
│   │       ├── user_tools.py              ✅ DONE
│   │       ├── post_tools.py              ✅ DONE (import fix in Increment 5)
│   │       ├── reply_tools.py             ✅ DONE (import fix in Increment 5)
│   │       └── vote_tools.py              ✅ DONE (import fix in Increment 5)
│   ├── middleware/
│   │   └── __init__.py
│   ├── utils/
│   │   └── __init__.py
│   └── exceptions.py                      ✅ DONE
├── tests/                                  ✅ Moved from docker/tests/ (Increment 5)
│   ├── __init__.py
│   ├── conftest.py                        ✅ DONE (updated with all fixtures)
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── test_user_tools.py             ✅ DONE (8 tests passing)
│   │   ├── test_post_tools.py             ✅ DONE (11 tests passing)
│   │   ├── test_reply_tools.py            ✅ DONE (10 tests passing)
│   │   └── test_vote_tools.py             ✅ DONE (8 tests passing)
│   └── fixtures/
│       └── __init__.py
├── docker/
│   ├── docker-compose.yml                 ✅ DONE
│   ├── .env.development                   ✅ DONE
│   └── .env.example                       ✅ DONE
├── pyproject.toml                         ✅ UPDATED
└── postgres_migration.md                  ✅ THIS FILE
```

---

## 💾 Memory Update Needed

After completing each major increment, create a memory with:
- Title: "AI Forum: Completed Increment X - [Feature]"
- Content: What was built, key decisions, test results
- Tags: ["ai-forum", "postgres-migration", "increment-complete"]
- Importance: 8
- Project: AI Forum - Memento AI (project_id: 26)

---

## 🎯 Next Session Start Here

1. **Verify environment:**
   ```bash
   cd /home/scott/development/ai/ai_forum
   docker ps | grep ai-forum-db  # Should be running
   ```

2. **Test MCP server startup:**
   ```bash
   cd /home/scott/development/ai/ai_forum
   ENVIRONMENT=development POSTGRES_HOST=127.0.0.1 POSTGRES_USER=ai_forum POSTGRES_PASSWORD=ai_forum_dev_password POSTGRES_DB=ai_forum uv run python main.py
   # Should see: "AI Forum MCP Server ready" and FastMCP banner
   ```

3. **Run full test suite to confirm Increments 1-5 work:**
   ```bash
   cd /home/scott/development/ai/ai_forum
   ENVIRONMENT=development POSTGRES_HOST=127.0.0.1 POSTGRES_USER=ai_forum POSTGRES_PASSWORD=ai_forum_dev_password POSTGRES_DB=ai_forum uv run pytest tests/e2e/ -v
   # Should see: 37 passed (8 user + 11 post + 10 reply + 8 vote tests)
   ```

4. **Start Increment 6 (Production Deployment):**
   - Provision Koyeb PostgreSQL database
   - Get database credentials from Koyeb dashboard
   - Create `.env.production` with production credentials
   - Deploy to Koyeb
   - Verify database initialization in production
   - Test MCP tools in production environment
   - Celebrate completion! 🎉

---

**Last Updated:** January 2025 (Increment 5 Complete)
**By:** Veridian (Claude Code Assistant)
