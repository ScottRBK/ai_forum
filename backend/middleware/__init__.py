"""Middleware for the AI Forum MCP server."""

from backend.middleware.user_identification import UserIdentificationMiddleware

__all__ = ["UserIdentificationMiddleware"]
