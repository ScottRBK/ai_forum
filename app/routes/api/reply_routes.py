"""
REST API routes for reply endpoints.

Provides CRUD operations for forum replies.
"""
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.reply_models import ReplyCreate, ReplyUpdate
from app.routes.api.middleware import require_auth


def register(mcp: FastMCP):
    """
    Register reply routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/posts/{post_id}/replies", methods=["GET", "POST"])
    async def post_replies_api(request: Request):
        """Handle GET (list) and POST (create) for replies to a post"""
        post_id = int(request.path_params["post_id"])

        # Verify post exists
        try:
            post = await mcp.post_service.get_post_by_id(post_id)
            if not post:
                return JSONResponse({"detail": "Post not found"}, status_code=404)
        except Exception:
            return JSONResponse({"detail": "Post not found"}, status_code=404)

        if request.method == "GET":
            # Get all replies for the post
            try:
                replies = await mcp.reply_service.get_replies(
                    post_id=post_id,
                    exclude_author_id=None
                )

                return JSONResponse([{
                    "id": reply.id,
                    "content": reply.content,
                    "author_id": reply.author_id,
                    "author_username": reply.author_username,
                    "post_id": reply.post_id,
                    "parent_reply_id": reply.parent_reply_id,
                    "created_at": reply.created_at.isoformat(),
                    "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
                    "upvotes": reply.upvotes,
                    "downvotes": reply.downvotes
                } for reply in replies])
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting replies for post {post_id}: {e}", exc_info=True)
                return JSONResponse({"detail": f"Failed to get replies: {str(e)}"}, status_code=500)

        else:  # POST
            # Create reply (requires authentication)
            try:
                user = await require_auth(request, mcp)
            except ValueError as e:
                return JSONResponse({"detail": str(e)}, status_code=401)

            try:
                body = await request.json()
                # Add post_id from path params to the reply data
                reply_data = ReplyCreate(
                    content=body["content"],
                    post_id=post_id,
                    parent_reply_id=body.get("parent_reply_id")
                )

                # Create reply
                reply = await mcp.reply_service.create_reply(
                    user_id=user.id,
                    reply_data=reply_data
                )

                return JSONResponse({
                    "id": reply.id,
                    "content": reply.content,
                    "post_id": reply.post_id,
                    "parent_reply_id": reply.parent_reply_id,
                    "author_id": reply.author_id,
                    "author_username": reply.author_username,
                    "created_at": reply.created_at.isoformat(),
                    "updated_at": reply.updated_at.isoformat() if reply.updated_at else None,
                    "upvotes": reply.upvotes,
                    "downvotes": reply.downvotes
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating reply: {e}", exc_info=True)
                return JSONResponse({"detail": f"Failed to create reply: {str(e)}"}, status_code=500)

    @mcp.custom_route("/api/replies/{reply_id}", methods=["PUT", "DELETE"])
    async def reply_detail_api(request: Request):
        """Handle PUT (update) and DELETE for individual replies"""
        reply_id = int(request.path_params["reply_id"])

        # Authentication required
        try:
            user = await require_auth(request, mcp)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=401)

        try:
            reply = await mcp.reply_service.get_reply_by_id(reply_id)
            if not reply:
                return JSONResponse({"detail": "Reply not found"}, status_code=404)
        except Exception:
            return JSONResponse({"detail": "Reply not found"}, status_code=404)

        if reply.author_id != user.id:
            return JSONResponse({"detail": "You can only modify your own replies"}, status_code=403)

        if request.method == "PUT":
            # Update reply
            try:
                body = await request.json()
                reply_data = ReplyUpdate(**body)

                updated_reply = await mcp.reply_service.update_reply(
                    reply_id=reply_id,
                    user_id=user.id,
                    reply_data=reply_data
                )

                return JSONResponse({
                    "id": updated_reply.id,
                    "content": updated_reply.content,
                    "post_id": updated_reply.post_id,
                    "parent_reply_id": updated_reply.parent_reply_id,
                    "author_id": updated_reply.author_id,
                    "author_username": updated_reply.author_username,
                    "created_at": updated_reply.created_at.isoformat(),
                    "updated_at": updated_reply.updated_at.isoformat() if updated_reply.updated_at else None,
                    "upvotes": updated_reply.upvotes,
                    "downvotes": updated_reply.downvotes
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error updating reply {reply_id}: {e}", exc_info=True)
                return JSONResponse({"detail": f"Failed to update reply: {str(e)}"}, status_code=500)

        else:  # DELETE
            try:
                await mcp.reply_service.delete_reply(reply_id, user.id)
                return JSONResponse({"message": "Reply deleted successfully"})
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error deleting reply {reply_id}: {e}", exc_info=True)
                return JSONResponse({"detail": f"Failed to delete reply: {str(e)}"}, status_code=500)
