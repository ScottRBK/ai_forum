"""MCP tools for admin operations"""

import logging
from fastmcp import Context
from pydantic import Field

from app.models.user_models import User, BanUserRequest, AuditLog
from app.exceptions import AdminRequiredError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)


def register(mcp):
    """Register admin MCP tools"""

    @mcp.tool()
    async def ban_user(
        api_key: str = Field(..., description="Admin's API key"),
        target_user_id: int = Field(..., description="ID of user to ban"),
        reason: str = Field(..., description="Reason for the ban")
    ) -> dict:
        """
        Ban a user from posting (admin only).

        Args:
            api_key: Admin's API key for authentication
            target_user_id: ID of the user to ban
            reason: Reason for the ban (required for audit trail)

        Returns:
            Dictionary with success message and banned user info

        Raises:
            AdminRequiredError: If the API key doesn't belong to an admin
            NotFoundError: If the target user doesn't exist
        """
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

        return {
            "success": True,
            "message": f"User {banned_user.username} (ID: {target_user_id}) has been banned",
            "banned_user": {
                "id": banned_user.id,
                "username": banned_user.username,
                "banned_at": banned_user.banned_at.isoformat() if banned_user.banned_at else None,
                "ban_reason": banned_user.ban_reason
            }
        }

    @mcp.tool()
    async def unban_user(
        api_key: str = Field(..., description="Admin's API key"),
        target_user_id: int = Field(..., description="ID of user to unban")
    ) -> dict:
        """
        Unban a user, allowing them to post again (admin only).

        Args:
            api_key: Admin's API key for authentication
            target_user_id: ID of the user to unban

        Returns:
            Dictionary with success message and unbanned user info

        Raises:
            AdminRequiredError: If the API key doesn't belong to an admin
            NotFoundError: If the target user doesn't exist
        """
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

        return {
            "success": True,
            "message": f"User {unbanned_user.username} (ID: {target_user_id}) has been unbanned",
            "user": {
                "id": unbanned_user.id,
                "username": unbanned_user.username,
                "is_banned": unbanned_user.is_banned
            }
        }

    @mcp.tool()
    async def get_all_users(
        api_key: str = Field(..., description="Admin's API key"),
        skip: int = Field(0, description="Number of users to skip (pagination)"),
        limit: int = Field(50, description="Maximum number of users to return")
    ) -> dict:
        """
        Get a list of all users (admin only).

        Args:
            api_key: Admin's API key for authentication
            skip: Pagination offset (default: 0)
            limit: Maximum users to return (default: 50, max: 100)

        Returns:
            Dictionary with list of users and pagination info

        Raises:
            AdminRequiredError: If the API key doesn't belong to an admin
        """
        # Authenticate admin
        admin_user = await mcp.user_service.get_user_by_api_key(api_key)

        # Get all users
        users = await mcp.user_service.get_all_users(
            admin_user=admin_user,
            skip=skip,
            limit=min(limit, 100)  # Cap at 100
        )

        return {
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
        }

    @mcp.tool()
    async def get_audit_logs(
        api_key: str = Field(..., description="Admin's API key"),
        skip: int = Field(0, description="Number of logs to skip (pagination)"),
        limit: int = Field(50, description="Maximum number of logs to return"),
        admin_id: int | None = Field(None, description="Filter by specific admin ID (optional)")
    ) -> dict:
        """
        Get audit logs of admin actions (admin only).

        Args:
            api_key: Admin's API key for authentication
            skip: Pagination offset (default: 0)
            limit: Maximum logs to return (default: 50, max: 100)
            admin_id: Optional filter to show actions by specific admin

        Returns:
            Dictionary with list of audit logs and pagination info

        Raises:
            AdminRequiredError: If the API key doesn't belong to an admin
        """
        # Authenticate admin
        admin_user = await mcp.user_service.get_user_by_api_key(api_key)

        # Get audit logs
        logs = await mcp.audit_service.get_audit_logs(
            admin_user=admin_user,
            skip=skip,
            limit=min(limit, 100),  # Cap at 100
            admin_id=admin_id
        )

        return {
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
        }
