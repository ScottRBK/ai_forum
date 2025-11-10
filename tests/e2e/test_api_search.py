"""
End-to-end tests for REST API search endpoints

Requires:
- PostgreSQL running in Docker
- MCP server running: python main.py

Tests the complete stack: HTTP → REST API → Service → Repository → PostgreSQL

Note: Search is currently a placeholder returning empty results.
When search_posts is implemented in PostService, these tests should be updated.
"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_search_posts_empty_query_api_e2e(api_base_url):
    """Test GET /api/search with empty query returns empty list"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/search")

        assert response.status_code == 200
        data = response.json()

        # Should be an empty list
        assert isinstance(data, list)
        assert len(data) == 0


@pytest.mark.asyncio
async def test_search_posts_with_query_api_e2e(api_base_url):
    """Test GET /api/search with query parameter"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/search?q=test")

        assert response.status_code == 200
        data = response.json()

        # Currently returns empty list (search not implemented)
        # When implemented, this should return matching posts
        assert isinstance(data, list)
