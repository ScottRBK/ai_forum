"""User identification middleware for FastMCP context injection.

This middleware extracts the user's API key from HTTP headers and injects
the user_id into the FastMCP context, preventing LLM-based user spoofing attacks.
"""

from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import User


class UserIdentificationMiddleware(BaseHTTPMiddleware):
    """Middleware to identify users from API keys and inject user_id into context.

    Priority order for user identification:
    1. X-API-Key header (primary)
    2. x-api-key header (case variation)
    3. Authorization header with Bearer token
    4. None (anonymous access)

    The user_id is injected into FastMCP context via request.state.user_id,
    which tools can access via ctx.get_state("user_id").
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Extract API key from headers and inject user_id into request state."""
        user_id = await self._identify_user(request)

        # Inject user_id into request state for FastMCP context
        request.state.user_id = user_id

        response = await call_next(request)
        return response

    async def _identify_user(self, request: Request) -> Optional[str]:
        """Identify user from API key in headers.

        Returns:
            User ID string if authenticated, None for anonymous access
        """
        api_key = self._extract_api_key(request)

        if not api_key:
            return None

        # Look up user by API key
        db: Session = SessionLocal()
        try:
            user = db.query(User).filter(User.api_key == api_key).first()
            if user:
                return str(user.id)
            return None
        finally:
            db.close()

    def _extract_api_key(self, request: Request) -> Optional[str]:
        """Extract API key from various header formats.

        Supports multiple header variations for broad client compatibility:
        - X-API-Key
        - x-api-key
        - Authorization: Bearer <token>
        """
        # Check X-API-Key header (primary)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return api_key

        # Check lowercase variation
        api_key = request.headers.get("x-api-key")
        if api_key:
            return api_key

        # Check Authorization header with Bearer token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header.replace("Bearer ", "", 1).strip()

        return None
