"""Admin authorization utilities for AI Forum"""

from app.models.user_models import User
from app.exceptions import AdminRequiredError, UserBannedError


def require_admin(user: User) -> None:
    """
    Verify user has admin privileges.

    Args:
        user: Authenticated user object

    Raises:
        AdminRequiredError: If user is not an admin
    """
    if not user.is_admin:
        raise AdminRequiredError("Admin privileges required for this operation")


def check_not_banned(user: User) -> None:
    """
    Verify user is not banned.

    Args:
        user: Authenticated user object

    Raises:
        UserBannedError: If user is banned
    """
    if user.is_banned:
        reason_msg = f" Reason: {user.ban_reason}" if user.ban_reason else ""
        raise UserBannedError(f"User is banned from posting.{reason_msg}")


def is_author_or_admin(user: User, resource_author_id: int) -> bool:
    """
    Check if user is resource author or admin.

    Args:
        user: Authenticated user
        resource_author_id: ID of resource owner

    Returns:
        True if user is author or admin, False otherwise
    """
    return user.id == resource_author_id or user.is_admin
