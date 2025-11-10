"""
REST API routes for post endpoints.

Provides CRUD operations for forum posts.
"""
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.models.post_models import PostCreate, PostUpdate
from app.routes.api.middleware import require_auth


def register(mcp: FastMCP):
    """
    Register post routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/posts", methods=["GET", "POST"])
    async def posts_api(request: Request):
        """Handle GET (list) and POST (create) for posts"""

        if request.method == "GET":
            # List posts with pagination and filtering
            category_id = request.query_params.get("category_id")
            skip = int(request.query_params.get("skip", 0))
            limit = int(request.query_params.get("limit", 20))

            posts = await mcp.post_service.get_posts(
                category_id=int(category_id) if category_id else None,
                skip=skip,
                limit=limit
            )

            return JSONResponse([{
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "author_id": post.author_id,
                "author_username": post.author_username,
                "category_id": post.category_id,
                "category_name": post.category_name,
                "created_at": post.created_at.isoformat(),
                "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                "upvotes": post.upvotes,
                "downvotes": post.downvotes,
                "reply_count": post.reply_count
            } for post in posts])

        else:  # POST
            # Create new post (requires authentication)
            try:
                user = await require_auth(request, mcp)
            except ValueError as e:
                return JSONResponse({"detail": str(e)}, status_code=401)

            try:
                body = await request.json()
                post_data = PostCreate(**body)

                # Verify category exists
                category = await mcp.category_service.get_category_by_id(post_data.category_id)
                if not category:
                    return JSONResponse({"detail": "Category not found"}, status_code=404)

                # Create post
                post = await mcp.post_service.create_post(
                    user_id=user.id,
                    post_data=post_data
                )

                return JSONResponse({
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author_id": post.author_id,
                    "author_username": post.author_username,
                    "category_id": post.category_id,
                    "category_name": post.category_name,
                    "created_at": post.created_at.isoformat(),
                    "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                    "upvotes": post.upvotes,
                    "downvotes": post.downvotes,
                    "reply_count": post.reply_count
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating post: {e}", exc_info=True)
                return JSONResponse({"detail": f"Failed to create post: {str(e)}"}, status_code=500)

    @mcp.custom_route("/api/posts/{post_id}", methods=["GET", "PUT", "DELETE"])
    async def post_detail_api(request: Request):
        """Handle GET (retrieve), PUT (update), and DELETE for individual posts"""
        post_id = int(request.path_params["post_id"])

        if request.method == "GET":
            # Get post details
            try:
                post = await mcp.post_service.get_post_by_id(post_id)
                if not post:
                    return JSONResponse({"detail": "Post not found"}, status_code=404)

                return JSONResponse({
                    "id": post.id,
                    "title": post.title,
                    "content": post.content,
                    "author_id": post.author_id,
                    "author_username": post.author_username,
                    "category_id": post.category_id,
                    "category_name": post.category_name,
                    "created_at": post.created_at.isoformat(),
                    "updated_at": post.updated_at.isoformat() if post.updated_at else None,
                    "upvotes": post.upvotes,
                    "downvotes": post.downvotes,
                    "reply_count": post.reply_count
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error getting post {post_id}: {e}", exc_info=True)
                return JSONResponse({"detail": "Post not found"}, status_code=404)

        # Authentication required for PUT and DELETE
        try:
            user = await require_auth(request, mcp)
        except ValueError as e:
            return JSONResponse({"detail": str(e)}, status_code=401)

        post = await mcp.post_service.get_post_by_id(post_id)
        if not post:
            return JSONResponse({"detail": "Post not found"}, status_code=404)

        if post.author_id != user.id and not user.is_admin:
            return JSONResponse({"detail": "You can only modify your own posts (unless admin)"}, status_code=403)

        if request.method == "PUT":
            # Update post
            body = await request.json()
            post_data = PostUpdate(**body)

            updated_post = await mcp.post_service.update_post(
                post_id=post_id,
                user=user,
                post_data=post_data
            )

            return JSONResponse({
                "id": updated_post.id,
                "title": updated_post.title,
                "content": updated_post.content,
                "author_id": updated_post.author_id,
                "author_username": updated_post.author_username,
                "category_id": updated_post.category_id,
                "category_name": updated_post.category_name,
                "created_at": updated_post.created_at.isoformat(),
                "updated_at": updated_post.updated_at.isoformat() if updated_post.updated_at else None,
                "upvotes": updated_post.upvotes,
                "downvotes": updated_post.downvotes,
                "reply_count": updated_post.reply_count
            })

        else:  # DELETE
            await mcp.post_service.delete_post(post_id, user)
            return JSONResponse({"message": "Post deleted successfully"})
