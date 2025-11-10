"""Service layer for audit log operations"""

import logging
from app.repositories.postgres.audit_log_repository import PostgresAuditLogRepository
from app.models.user_models import User, AuditLog
from app.utils.admin_utils import require_admin

logger = logging.getLogger(__name__)


class AuditService:
    """Service for audit log operations"""

    def __init__(self, audit_log_repository: PostgresAuditLogRepository):
        self.audit_log_repository = audit_log_repository

    async def log_admin_action(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int,
        details: str | None = None
    ) -> AuditLog:
        """
        Log an admin action to the audit trail.

        Args:
            admin_id: ID of admin performing the action
            action: Action performed (e.g., "delete_post", "ban_user", "unban_user")
            target_type: Type of resource (e.g., "post", "reply", "user")
            target_id: ID of the target resource
            details: Optional additional details (JSON string or plain text)

        Returns:
            Created audit log entry
        """
        audit_log = await self.audit_log_repository.create_audit_log(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details
        )

        logger.info(
            "Admin action logged",
            extra={
                "admin_id": admin_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id
            }
        )

        return audit_log

    async def get_audit_logs(
        self,
        admin_user: User,
        skip: int = 0,
        limit: int = 50,
        admin_id: int | None = None
    ) -> list[AuditLog]:
        """
        Get audit logs (admin only).

        Args:
            admin_user: Authenticated admin user
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            admin_id: Optional filter by specific admin ID

        Returns:
            List of audit logs ordered by created_at descending

        Raises:
            AdminRequiredError: If user is not an admin
        """
        require_admin(admin_user)

        return await self.audit_log_repository.get_audit_logs(
            skip=skip,
            limit=limit,
            admin_id=admin_id
        )
