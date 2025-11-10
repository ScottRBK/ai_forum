"""User repository for PostgreSQL data access operations"""

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
import logging

from app.repositories.postgres.postgres_tables import UsersTable
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.models.user_models import User, UserCreate, UserUpdate
from app.exceptions import NotFoundError, DuplicateError

logger = logging.getLogger(__name__)


class PostgresUserRepository:
    """Repository for User entity operations in Postgres"""

    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def get_user_by_id(self, user_id: int) -> User | None:
        """
        Get a user by their ID

        Args:
            user_id: User ID

        Returns:
            User object or None if not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.id == user_id)
            )
            user_orm = result.scalars().first()
            if user_orm:
                return User.model_validate(user_orm)
            return None

    async def get_user_by_username(self, username: str) -> User | None:
        """
        Get a user by their username

        Args:
            username: Username to search for

        Returns:
            User object or None if not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.username == username)
            )
            user_orm = result.scalars().first()
            if user_orm:
                return User.model_validate(user_orm)
            return None

    async def get_user_by_api_key(self, api_key: str) -> User | None:
        """
        Get a user by their API key

        Args:
            api_key: API key to search for

        Returns:
            User object or None if not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.api_key == api_key)
            )
            user_orm = result.scalars().first()
            if user_orm:
                return User.model_validate(user_orm)
            return None

    async def create_user(self, username: str, api_key: str, verification_score: int = 0) -> User:
        """
        Create a new user

        Args:
            username: Username for the new user
            api_key: Generated API key
            verification_score: Initial verification score

        Returns:
            Created User object

        Raises:
            DuplicateError: If username or API key already exists
        """
        async with self.db_adapter.session() as session:
            # Check for duplicate username
            existing = await session.execute(
                select(UsersTable).where(UsersTable.username == username)
            )
            if existing.scalars().first():
                raise DuplicateError(f"Username '{username}' already exists")

            # Create new user
            new_user = UsersTable(
                username=username,
                api_key=api_key,
                verification_score=verification_score
            )
            session.add(new_user)
            await session.flush()
            await session.refresh(new_user)

            logger.info(
                "User created successfully",
                extra={"user_id": new_user.id, "username": username}
            )

            return User.model_validate(new_user)

    async def update_user(self, user_id: int, updated_user: UserUpdate) -> User:
        """
        Update an existing user

        Args:
            user_id: User ID to update
            updated_user: UserUpdate object with fields to update

        Returns:
            Updated User object

        Raises:
            NotFoundError: If user not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.id == user_id)
            )
            user_orm = result.scalars().first()

            if not user_orm:
                raise NotFoundError(f"User with ID {user_id} not found")

            # Update only provided fields
            update_data = updated_user.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(user_orm, field, value)

            await session.flush()
            await session.refresh(user_orm)

            logger.info(
                "User updated successfully",
                extra={"user_id": user_id, "updated_fields": list(update_data.keys())}
            )

            return User.model_validate(user_orm)

    async def delete_user(self, user_id: int) -> None:
        """
        Delete a user

        Args:
            user_id: User ID to delete

        Raises:
            NotFoundError: If user not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.id == user_id)
            )
            user_orm = result.scalars().first()

            if not user_orm:
                raise NotFoundError(f"User with ID {user_id} not found")

            await session.delete(user_orm)

            logger.info(
                "User deleted successfully",
                extra={"user_id": user_id}
            )

    async def get_all_users(self, skip: int = 0, limit: int = 50) -> list[User]:
        """
        Get all users with pagination (admin only operation).

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of User objects
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable)
                .order_by(UsersTable.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            user_rows = result.scalars().all()
            return [User.model_validate(row) for row in user_rows]

    async def ban_user(self, user_id: int, admin_id: int, reason: str) -> User:
        """
        Ban a user (admin only operation).

        Args:
            user_id: ID of user to ban
            admin_id: ID of admin performing the ban
            reason: Reason for the ban

        Returns:
            Updated User object

        Raises:
            NotFoundError: If user not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.id == user_id)
            )
            user_orm = result.scalars().first()

            if not user_orm:
                raise NotFoundError(f"User with ID {user_id} not found")

            # Update ban fields
            from datetime import datetime, timezone
            user_orm.is_banned = True
            user_orm.banned_at = datetime.now(timezone.utc)
            user_orm.banned_by = admin_id
            user_orm.ban_reason = reason

            await session.flush()
            await session.refresh(user_orm)

            logger.info(
                "User banned successfully",
                extra={"user_id": user_id, "admin_id": admin_id, "reason": reason}
            )

            return User.model_validate(user_orm)

    async def unban_user(self, user_id: int) -> User:
        """
        Unban a user (admin only operation).

        Args:
            user_id: ID of user to unban

        Returns:
            Updated User object

        Raises:
            NotFoundError: If user not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(UsersTable).where(UsersTable.id == user_id)
            )
            user_orm = result.scalars().first()

            if not user_orm:
                raise NotFoundError(f"User with ID {user_id} not found")

            # Clear ban fields
            user_orm.is_banned = False
            user_orm.banned_at = None
            user_orm.banned_by = None
            user_orm.ban_reason = None

            await session.flush()
            await session.refresh(user_orm)

            logger.info(
                "User unbanned successfully",
                extra={"user_id": user_id}
            )

            return User.model_validate(user_orm)
