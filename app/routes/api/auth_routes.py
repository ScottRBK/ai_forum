"""
REST API routes for authentication endpoints.

Provides challenge-based authentication for AI agents.
"""
import logging
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.user_models import UserCreate
from app.exceptions import (
    AIForumException,
    AuthenticationError,
    DuplicateError,
    ValidationError
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    """
    Register authentication routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/auth/challenge", methods=["GET"])
    async def get_challenge_api(request: Request):
        """Get a reverse CAPTCHA challenge to prove you're an AI"""
        challenge = mcp.user_service.request_challenge()
        return JSONResponse({
            "challenge_id": challenge.challenge_id,
            "challenge_type": challenge.challenge_type,
            "question": challenge.question
        })

    @mcp.custom_route("/api/auth/register", methods=["POST"])
    async def register_user_api(request: Request):
        """Register a new AI agent account"""
        body = await request.json()
        user_data = UserCreate(**body)

        # Use the user service's register_user method (handles verification)
        try:
            user = await mcp.user_service.register_user(
                username=user_data.username,
                challenge_id=user_data.challenge_id,
                answer=user_data.answer
            )

            return JSONResponse({
                "id": user.id,
                "username": user.username,
                "api_key": user.api_key,
                "created_at": user.created_at.isoformat()
            })
        except (AuthenticationError, DuplicateError, ValidationError) as e:
            # Handle expected business logic errors (400 Bad Request)
            logger.warning(f"Registration failed with business logic error: {e}")
            return JSONResponse(
                {"detail": str(e)},
                status_code=400
            )
        except AIForumException as e:
            # Handle other application errors (500 Internal Server Error)
            logger.error(f"Registration failed with application error: {e}")
            return JSONResponse(
                {"detail": str(e)},
                status_code=500
            )
        except Exception as e:
            # Handle unexpected errors
            logger.exception(f"Registration failed with unexpected exception: {e}")
            return JSONResponse(
                {"detail": "Registration failed"},
                status_code=500
            )
