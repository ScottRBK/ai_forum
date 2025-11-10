"""
REST API route modules for AI Forum.
"""
from app.routes.api import auth_routes, category_routes, post_routes, reply_routes, vote_routes, search_routes

__all__ = ["auth_routes", "category_routes", "post_routes", "reply_routes", "vote_routes", "search_routes"]
