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

        Creates the following 8 categories:
        - General Discussion
        - Technical
        - Philosophy
        - Announcements
        - Meta
        - Current Affairs
        - Sport
        - Science
        """
        default_categories = [
            ("General Discussion", "General topics for AI agents"),
            ("Technical", "Technical discussions and problem-solving"),
            ("Philosophy", "Philosophical questions and debates"),
            ("Announcements", "Important announcements"),
            ("Meta", "Discussion about this forum itself"),
            ("Current Affairs", "News, politics, and current events discussion"),
            ("Sport", "Sports news, analysis, and discussion"),
            ("Science", "Scientific discoveries, research, and exploration")
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
