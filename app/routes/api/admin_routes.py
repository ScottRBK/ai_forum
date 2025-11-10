"""
REST API routes for admin operations.

Provides endpoints for user management, banning, and audit logs.
"""
import logging
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.exceptions import (
    AIForumException,
    AuthenticationError,
    AdminRequiredError,
    NotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)


def register(mcp: FastMCP):
    """
    Register admin routes with the FastMCP application.

    Args:
        mcp: FastMCP instance with attached services
    """

    @mcp.custom_route("/api/admin/ban-user", methods=["POST"])
    async def ban_user_api(request: Request):
        """Ban a user from posting (admin only)"""
        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            if not api_key:
                return JSONResponse(
                    {"detail": "X-API-Key header required"},
                    status_code=401
                )

            # Parse request body
            body = await request.json()
            target_user_id = body.get("target_user_id")
            reason = body.get("reason")

            if not target_user_id or not reason:
                return JSONResponse(
                    {"detail": "target_user_id and reason are required"},
                    status_code=400
                )

            # Authenticate admin
            admin_user = await mcp.user_service.get_user_by_api_key(api_key)

            # Ban the user
            banned_user = await mcp.user_service.ban_user(
                target_user_id=target_user_id,
                admin_user=admin_user,
                reason=reason
            )

            # Log the admin action
            await mcp.audit_service.log_admin_action(
                admin_id=admin_user.id,
                action="ban_user",
                target_type="user",
                target_id=target_user_id,
                details=f"Reason: {reason}"
            )

            return JSONResponse({
                "success": True,
                "message": f"User {banned_user.username} (ID: {target_user_id}) has been banned",
                "banned_user": {
                    "id": banned_user.id,
                    "username": banned_user.username,
                    "banned_at": banned_user.banned_at.isoformat() if banned_user.banned_at else None,
                    "ban_reason": banned_user.ban_reason
                }
            })
        except AdminRequiredError as e:
            logger.warning(f"Admin required for ban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=403)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for ban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=401)
        except ValidationError as e:
            logger.warning(f"Validation error for ban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=400)
        except NotFoundError as e:
            logger.warning(f"User not found for ban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=404)
        except AIForumException as e:
            logger.error(f"Error banning user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=500)
        except Exception as e:
            logger.exception(f"Unexpected error in ban_user: {e}")
            return JSONResponse({"detail": "Failed to ban user"}, status_code=500)

    @mcp.custom_route("/api/admin/unban-user", methods=["POST"])
    async def unban_user_api(request: Request):
        """Unban a user, allowing them to post again (admin only)"""
        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            if not api_key:
                return JSONResponse(
                    {"detail": "X-API-Key header required"},
                    status_code=401
                )

            # Parse request body
            body = await request.json()
            target_user_id = body.get("target_user_id")

            if not target_user_id:
                return JSONResponse(
                    {"detail": "target_user_id is required"},
                    status_code=400
                )

            # Authenticate admin
            admin_user = await mcp.user_service.get_user_by_api_key(api_key)

            # Unban the user
            unbanned_user = await mcp.user_service.unban_user(
                target_user_id=target_user_id,
                admin_user=admin_user
            )

            # Log the admin action
            await mcp.audit_service.log_admin_action(
                admin_id=admin_user.id,
                action="unban_user",
                target_type="user",
                target_id=target_user_id,
                details=None
            )

            return JSONResponse({
                "success": True,
                "message": f"User {unbanned_user.username} (ID: {target_user_id}) has been unbanned",
                "user": {
                    "id": unbanned_user.id,
                    "username": unbanned_user.username,
                    "is_banned": unbanned_user.is_banned
                }
            })
        except AdminRequiredError as e:
            logger.warning(f"Admin required for unban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=403)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for unban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=401)
        except NotFoundError as e:
            logger.warning(f"User not found for unban_user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=404)
        except AIForumException as e:
            logger.error(f"Error unbanning user: {e}")
            return JSONResponse({"detail": str(e)}, status_code=500)
        except Exception as e:
            logger.exception(f"Unexpected error in unban_user: {e}")
            return JSONResponse({"detail": "Failed to unban user"}, status_code=500)

    @mcp.custom_route("/api/admin/users", methods=["GET"])
    async def get_all_users_api(request: Request):
        """Get a list of all users with pagination (admin only)"""
        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            if not api_key:
                return JSONResponse(
                    {"detail": "X-API-Key header required"},
                    status_code=401
                )

            # Get pagination parameters
            skip = int(request.query_params.get("skip", 0))
            limit = int(request.query_params.get("limit", 50))
            limit = min(limit, 100)  # Cap at 100

            # Authenticate admin
            admin_user = await mcp.user_service.get_user_by_api_key(api_key)

            # Get all users
            users = await mcp.user_service.get_all_users(
                admin_user=admin_user,
                skip=skip,
                limit=limit
            )

            return JSONResponse({
                "users": [
                    {
                        "id": user.id,
                        "username": user.username,
                        "is_admin": user.is_admin,
                        "is_banned": user.is_banned,
                        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
                        "ban_reason": user.ban_reason,
                        "created_at": user.created_at.isoformat()
                    }
                    for user in users
                ],
                "count": len(users),
                "skip": skip,
                "limit": limit
            })
        except AdminRequiredError as e:
            logger.warning(f"Admin required for get_all_users: {e}")
            return JSONResponse({"detail": str(e)}, status_code=403)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for get_all_users: {e}")
            return JSONResponse({"detail": str(e)}, status_code=401)
        except AIForumException as e:
            logger.error(f"Error getting users: {e}")
            return JSONResponse({"detail": str(e)}, status_code=500)
        except Exception as e:
            logger.exception(f"Unexpected error in get_all_users: {e}")
            return JSONResponse({"detail": "Failed to get users"}, status_code=500)

    @mcp.custom_route("/api/admin/audit-logs", methods=["GET"])
    async def get_audit_logs_api(request: Request):
        """Get audit logs of admin actions (admin only)"""
        try:
            # Get API key from header
            api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
            if not api_key:
                return JSONResponse(
                    {"detail": "X-API-Key header required"},
                    status_code=401
                )

            # Get pagination and filter parameters
            skip = int(request.query_params.get("skip", 0))
            limit = int(request.query_params.get("limit", 50))
            limit = min(limit, 100)  # Cap at 100
            admin_id = request.query_params.get("admin_id")
            if admin_id:
                admin_id = int(admin_id)

            # Authenticate admin
            admin_user = await mcp.user_service.get_user_by_api_key(api_key)

            # Get audit logs
            logs = await mcp.audit_service.get_audit_logs(
                admin_user=admin_user,
                skip=skip,
                limit=limit,
                admin_id=admin_id
            )

            return JSONResponse({
                "audit_logs": [
                    {
                        "id": log.id,
                        "admin_id": log.admin_id,
                        "action": log.action,
                        "target_type": log.target_type,
                        "target_id": log.target_id,
                        "details": log.details,
                        "created_at": log.created_at.isoformat()
                    }
                    for log in logs
                ],
                "count": len(logs),
                "skip": skip,
                "limit": limit,
                "filtered_by_admin": admin_id
            })
        except AdminRequiredError as e:
            logger.warning(f"Admin required for get_audit_logs: {e}")
            return JSONResponse({"detail": str(e)}, status_code=403)
        except AuthenticationError as e:
            logger.warning(f"Authentication failed for get_audit_logs: {e}")
            return JSONResponse({"detail": str(e)}, status_code=401)
        except AIForumException as e:
            logger.error(f"Error getting audit logs: {e}")
            return JSONResponse({"detail": str(e)}, status_code=500)
        except Exception as e:
            logger.exception(f"Unexpected error in get_audit_logs: {e}")
            return JSONResponse({"detail": "Failed to get audit logs"}, status_code=500)
