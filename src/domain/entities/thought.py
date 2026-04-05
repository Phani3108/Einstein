"""Thought domain entity for the Personal Semantic Engine."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.entities.semantic_entry import SemanticEntry


class GeoLocation(BaseModel):
    """Geographic location information."""

    latitude: float
    longitude: float
    name: Optional[str] = None


class WeatherData(BaseModel):
    """Weather information."""

    temperature: Optional[float] = None
    condition: Optional[str] = None
    humidity: Optional[float] = None


class ThoughtMetadata(BaseModel):
    """Metadata associated with a thought."""

    location: Optional[GeoLocation] = None
    weather: Optional[WeatherData] = None
    mood: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    custom: Dict[str, str] = Field(default_factory=dict)


class Thought(BaseModel):
    """A user's thought or note with associated metadata and semantic entries."""

    id: UUID
    user_id: UUID
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: ThoughtMetadata = Field(default_factory=ThoughtMetadata)
    semantic_entries: List[SemanticEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @validator("content")
    def content_not_empty(cls, v: str) -> str:
        """Validate that the thought content is not empty.

        Args:
            v: The content to validate

        Returns:
            The validated content

        Raises:
            ValueError: If the content is empty
        """
        if not v.strip():
            raise ValueError("Thought content cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects
