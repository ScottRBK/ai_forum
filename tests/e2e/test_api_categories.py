"""
End-to-end tests for REST API category endpoints

Requires:
- PostgreSQL running in Docker
- MCP server running: python main.py

Tests the complete stack: HTTP → REST API → Service → Repository → PostgreSQL
"""
import pytest
import httpx


@pytest.mark.asyncio
async def test_get_categories_api_e2e(api_base_url):
    """Test GET /api/categories returns all categories"""
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/api/categories")

        assert response.status_code == 200
        data = response.json()

        # Should be a list
        assert isinstance(data, list)

        # Should have at least the default categories
        assert len(data) > 0

        # Each category should have required fields
        for category in data:
            assert "id" in category
            assert "name" in category
            assert "description" in category
            assert isinstance(category["id"], int)
            assert isinstance(category["name"], str)
            assert isinstance(category["description"], str)
