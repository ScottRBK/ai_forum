"""
E2E test fixtures for AI Forum MCP server

Tests connect to a running MCP server via HTTP and validate
the complete stack: HTTP → FastMCP → Service → Repository → PostgreSQL
"""
import pytest
from app.config.settings import settings


@pytest.fixture
def mcp_server_url():
    """Returns the MCP protocol endpoint URL for E2E tests"""
    return f"http://localhost:{settings.SERVER_PORT}/mcp"


@pytest.fixture
def api_base_url():
    """Returns the REST API base URL for E2E tests"""
    return f"http://localhost:{settings.SERVER_PORT}"
