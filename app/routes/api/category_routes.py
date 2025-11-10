"""
REST API routes for category endpoints.

Provides category browsing for the forum.
"""
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def register(mcp: FastMCP):
    """
    Register category routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/categories", methods=["GET"])
    async def get_categories_api(request: Request):
        """Get all categories for frontend"""
        categories = await mcp.category_service.get_all_categories()
        return JSONResponse([
            {"id": cat.id, "name": cat.name, "description": cat.description}
            for cat in categories
        ])
