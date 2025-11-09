"""Category domain models"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Category(BaseModel):
    """Category domain model"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    created_at: datetime


class CategoryResponse(BaseModel):
    """Category response for MCP tools"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
