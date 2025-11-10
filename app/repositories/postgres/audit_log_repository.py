"""PostgreSQL repository for audit logs"""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import AuditLogsTable
from app.models.user_models import AuditLog
from app.exceptions import NotFoundError


class PostgresAuditLogRepository:
    """Repository for audit log operations"""

    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def create_audit_log(
        self,
        admin_id: int,
        action: str,
        target_type: str,
        target_id: int,
        details: str | None = None
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            admin_id: ID of admin performing the action
            action: Action performed (e.g., "delete_post", "ban_user")
            target_type: Type of resource (e.g., "post", "reply", "user")
            target_id: ID of the target resource
            details: Optional additional details (JSON string)

        Returns:
            AuditLog: Created audit log

        Raises:
            SQLAlchemyError: If database operation fails
        """
        async with self.db_adapter.session() as session:
            audit_log_row = AuditLogsTable(
                admin_id=admin_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details=details
            )
            session.add(audit_log_row)
            await session.flush()
            await session.refresh(audit_log_row)

            return AuditLog.model_validate(audit_log_row)

    async def get_audit_logs(
        self,
        skip: int = 0,
        limit: int = 50,
        admin_id: int | None = None
    ) -> list[AuditLog]:
        """
        Get audit logs with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            admin_id: Optional filter by admin ID

        Returns:
            List of audit logs ordered by created_at descending
        """
        async with self.db_adapter.session() as session:
            query = select(AuditLogsTable).order_by(AuditLogsTable.created_at.desc())

            if admin_id is not None:
                query = query.where(AuditLogsTable.admin_id == admin_id)

            query = query.offset(skip).limit(limit)
            result = await session.execute(query)
            audit_log_rows = result.scalars().all()

            return [AuditLog.model_validate(row) for row in audit_log_rows]
