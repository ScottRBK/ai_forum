"""Category repository for database operations"""

import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.category_models import Category
from app.repositories.postgres.postgres_adapter import PostgresDatabaseAdapter
from app.repositories.postgres.postgres_tables import CategoriesTable
from app.exceptions import DuplicateError

logger = logging.getLogger(__name__)


class PostgresCategoryRepository:
    """Repository for category database operations"""

    def __init__(self, db_adapter: PostgresDatabaseAdapter):
        self.db_adapter = db_adapter

    async def get_all_categories(self) -> List[Category]:
        """
        Get all categories.

        Returns:
            List of Category domain models
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(CategoriesTable).order_by(CategoriesTable.name)
            )
            categories = result.scalars().all()

            logger.info(
                "Retrieved categories",
                extra={"count": len(categories)}
            )

            return [Category.model_validate(cat) for cat in categories]

    async def get_category_by_id(self, category_id: int) -> Category | None:
        """
        Get category by ID.

        Args:
            category_id: Category ID to retrieve

        Returns:
            Category domain model or None if not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(CategoriesTable).where(CategoriesTable.id == category_id)
            )
            category_orm = result.scalars().first()

            if category_orm:
                logger.info(
                    "Retrieved category",
                    extra={"category_id": category_id, "name": category_orm.name}
                )
                return Category.model_validate(category_orm)

            logger.warning(
                "Category not found",
                extra={"category_id": category_id}
            )
            return None

    async def get_category_by_name(self, name: str) -> Category | None:
        """
        Get category by name.

        Args:
            name: Category name to search for

        Returns:
            Category domain model or None if not found
        """
        async with self.db_adapter.session() as session:
            result = await session.execute(
                select(CategoriesTable).where(CategoriesTable.name == name)
            )
            category_orm = result.scalars().first()

            if category_orm:
                return Category.model_validate(category_orm)
            return None

    async def create_category(self, name: str, description: str | None = None) -> Category:
        """
        Create a new category.

        Args:
            name: Category name
            description: Optional category description

        Returns:
            Created Category domain model

        Raises:
            DuplicateError: If category with this name already exists
        """
        async with self.db_adapter.session() as session:
            # Check for duplicate
            existing = await self.get_category_by_name(name)
            if existing:
                raise DuplicateError(f"Category with name '{name}' already exists")

            category = CategoriesTable(
                name=name,
                description=description
            )

            session.add(category)
            await session.flush()
            await session.refresh(category)

            logger.info(
                "Created category",
                extra={"category_id": category.id, "name": name}
            )

            return Category.model_validate(category)
