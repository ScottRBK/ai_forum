"""Pytest configuration and fixtures for AI Forum tests"""

import pytest
import pytest_asyncio
import asyncio

from app.config.settings import settings
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import Base
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


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_adapter():
    """Create a fresh database adapter for each test."""
    adapter = PostgresDatabaseAdapter()
    await adapter.init_db()

    # Clean database
    async with adapter._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield adapter

    await adapter.dispose()


@pytest.fixture
def user_repository(db_adapter: PostgresDatabaseAdapter) -> PostgresUserRepository:
    """Create a user repository instance for tests"""
    return PostgresUserRepository(db_adapter)


@pytest.fixture
def user_service(user_repository: PostgresUserRepository) -> UserService:
    """Create a user service instance for tests"""
    return UserService(user_repository)


@pytest.fixture
def category_repository(db_adapter: PostgresDatabaseAdapter) -> PostgresCategoryRepository:
    """Create a category repository instance for tests"""
    return PostgresCategoryRepository(db_adapter)


@pytest.fixture
def category_service(category_repository: PostgresCategoryRepository) -> CategoryService:
    """Create a category service instance for tests"""
    return CategoryService(category_repository)


@pytest.fixture
def post_repository(db_adapter: PostgresDatabaseAdapter) -> PostgresPostRepository:
    """Create a post repository instance for tests"""
    return PostgresPostRepository(db_adapter)


@pytest.fixture
def post_service(post_repository: PostgresPostRepository) -> PostService:
    """Create a post service instance for tests"""
    return PostService(post_repository)


@pytest.fixture
def reply_repository(db_adapter: PostgresDatabaseAdapter) -> PostgresReplyRepository:
    """Create a reply repository instance for tests"""
    return PostgresReplyRepository(db_adapter)


@pytest.fixture
def reply_service(reply_repository: PostgresReplyRepository) -> ReplyService:
    """Create a reply service instance for tests"""
    return ReplyService(reply_repository)


@pytest.fixture
def vote_repository(
    db_adapter: PostgresDatabaseAdapter,
    post_repository: PostgresPostRepository,
    reply_repository: PostgresReplyRepository
) -> PostgresVoteRepository:
    """Create a vote repository instance for tests"""
    return PostgresVoteRepository(db_adapter, post_repository, reply_repository)


@pytest.fixture
def vote_service(vote_repository: PostgresVoteRepository) -> VoteService:
    """Create a vote service instance for tests"""
    return VoteService(vote_repository)


@pytest.fixture
def audit_log_repository(db_adapter: PostgresDatabaseAdapter) -> PostgresAuditLogRepository:
    """Create an audit log repository instance for tests"""
    return PostgresAuditLogRepository(db_adapter)


@pytest.fixture
def audit_service(audit_log_repository: PostgresAuditLogRepository) -> AuditService:
    """Create an audit service instance for tests"""
    return AuditService(audit_log_repository)
