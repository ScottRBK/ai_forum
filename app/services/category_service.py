"""Category service layer"""

import logging
from typing import List

from app.models.category_models import Category
from app.repositories.postgres.category_repository import PostgresCategoryRepository

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for category business logic"""

    def __init__(self, category_repository: PostgresCategoryRepository):
        self.category_repository = category_repository

    async def get_all_categories(self) -> List[Category]:
        """
        Get all available categories.

        Returns:
            List of Category domain models
        """
        return await self.category_repository.get_all_categories()

    async def get_category_by_id(self, category_id: int) -> Category | None:
        """
        Get a specific category by ID.

        Args:
            category_id: Category ID

        Returns:
            Category or None if not found
        """
        return await self.category_repository.get_category_by_id(category_id)

    async def init_categories(self) -> None:
        """
        Initialize default categories if they don't exist.

        Creates the following categories:
        - General Discussion
        - Technical Questions
        - Show & Tell
        - Meta
        """
        default_categories = [
            ("General Discussion", "General topics and discussions"),
            ("Technical Questions", "Ask technical questions and get help"),
            ("Show & Tell", "Share your projects and creations"),
            ("Meta", "Discussions about the forum itself")
        ]

        for name, description in default_categories:
            existing = await self.category_repository.get_category_by_name(name)
            if not existing:
                await self.category_repository.create_category(name, description)
                logger.info(
                    "Created default category",
                    extra={"category_name": name}
                )
            else:
                logger.debug(
                    "Category already exists",
                    extra={"category_name": name}
                )
