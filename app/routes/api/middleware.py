"""
Shared middleware and utilities for REST API routes.
"""
from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastmcp import FastMCP

from app.models.user_models import User


async def require_auth(request: Request, mcp: FastMCP) -> User:
    """
    Centralized authentication helper for REST API routes.

    Extracts API key from X-API-Key header and validates it.

    Args:
        request: Starlette request object
        mcp: FastMCP instance with attached services

    Returns:
        User: Authenticated user object

    Raises:
        Returns JSONResponse with 401 status if authentication fails
    """
    # Extract API key from headers (case-insensitive)
    api_key: Optional[str] = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

    if not api_key:
        raise ValueError("Missing API key")

    # Validate API key and get user
    user = await mcp.user_service.get_user_by_api_key(api_key)

    if not user:
        raise ValueError("Invalid API key")

    return user


def error_response(status_code: int, message: str, detail: Optional[str] = None) -> JSONResponse:
    """
    Create standardized error response.

    Args:
        status_code: HTTP status code
        message: Error message
        detail: Optional detailed error information

    Returns:
        JSONResponse with error details
    """
    content = {"error": message}
    if detail:
        content["detail"] = detail

    return JSONResponse(content=content, status_code=status_code)
