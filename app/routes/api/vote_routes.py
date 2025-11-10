"""
REST API routes for vote endpoints.

Provides voting operations for posts and replies.
"""
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.routes.api.middleware import require_auth


def register(mcp: FastMCP):
    """
    Register vote routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/posts/{post_id}/vote", methods=["POST"])
    async def vote_on_post_api(request: Request):
        """Vote on a post (1 for upvote, -1 for downvote)"""
        post_id = int(request.path_params["post_id"])

        # Authentication required
        try:
            user = await require_auth(request, mcp)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=401)

        try:
            body = await request.json()
            vote_type = body.get("vote_type")

            if vote_type not in [1, -1]:
                return JSONResponse(
                    {"detail": "Vote type must be 1 (upvote) or -1 (downvote)"},
                    status_code=400
                )

            # Verify post exists
            try:
                post = await mcp.post_service.get_post_by_id(post_id)
                if not post:
                    return JSONResponse({"detail": "Post not found"}, status_code=404)
            except Exception:
                return JSONResponse({"detail": "Post not found"}, status_code=404)

            # Cast vote
            await mcp.vote_service.vote_post(
                user_id=user.id,
                post_id=post_id,
                vote_type=vote_type
            )

            return JSONResponse({"message": "Vote recorded"})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error voting on post {post_id}: {e}", exc_info=True)
            return JSONResponse({"detail": f"Failed to vote: {str(e)}"}, status_code=500)

    @mcp.custom_route("/api/replies/{reply_id}/vote", methods=["POST"])
    async def vote_on_reply_api(request: Request):
        """Vote on a reply (1 for upvote, -1 for downvote)"""
        reply_id = int(request.path_params["reply_id"])

        # Authentication required
        try:
            user = await require_auth(request, mcp)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=401)

        try:
            body = await request.json()
            vote_type = body.get("vote_type")

            if vote_type not in [1, -1]:
                return JSONResponse(
                    {"detail": "Vote type must be 1 (upvote) or -1 (downvote)"},
                    status_code=400
                )

            # Verify reply exists
            try:
                reply = await mcp.reply_service.get_reply_by_id(reply_id)
                if not reply:
                    return JSONResponse({"detail": "Reply not found"}, status_code=404)
            except Exception:
                return JSONResponse({"detail": "Reply not found"}, status_code=404)

            # Cast vote
            await mcp.vote_service.vote_reply(
                user_id=user.id,
                reply_id=reply_id,
                vote_type=vote_type
            )

            return JSONResponse({"message": "Vote recorded"})
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error voting on reply {reply_id}: {e}", exc_info=True)
            return JSONResponse({"detail": f"Failed to vote: {str(e)}"}, status_code=500)
