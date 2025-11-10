"""
REST API routes for search endpoints.

Provides search functionality for posts.
"""
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse


def register(mcp: FastMCP):
    """
    Register search routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/search", methods=["GET"])
    async def search_posts_api(request: Request):
        """Search posts for frontend"""
        query = request.query_params.get("q", "")

        if not query:
            return JSONResponse([])

        # TODO: Implement search in post service
        # For now, return empty results to avoid breaking the endpoint
        # When search_posts is implemented in PostService, use:
        # posts = await mcp.post_service.search_posts(query)
        # return JSONResponse([{
        #     "id": post.id,
        #     "title": post.title,
        #     "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
        #     "author_username": post.author_username,
        #     "category_name": post.category_name,
        #     "created_at": post.created_at.isoformat()
        # } for post in posts])

        return JSONResponse([])
