"""Semantic entry domain entity for the Personal Semantic Engine."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.entities.enums import EntityType


class Relationship(BaseModel):
    """A relationship between two semantic entries."""

    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    strength: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects


class SemanticEntry(BaseModel):
    """A semantic entity extracted from a thought."""

    id: UUID
    thought_id: UUID
    entity_type: EntityType
    entity_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: str
    relationships: List[Relationship] = Field(default_factory=list)
    embedding: Optional[List[float]] = None
    extracted_at: datetime = Field(default_factory=datetime.now)

    @validator("entity_value")
    def entity_value_not_empty(cls, v: str) -> str:
        """Validate that the entity value is not empty.

        Args:
            v: The entity value to validate

        Returns:
            The validated entity value

        Raises:
            ValueError: If the entity value is empty
        """
        if not v.strip():
            raise ValueError("Entity value cannot be empty")
        return v

    @validator("confidence")
    def confidence_in_range(cls, v: float) -> float:
        """Validate that the confidence is between 0 and 1.

        Args:
            v: The confidence to validate

        Returns:
            The validated confidence

        Raises:
            ValueError: If the confidence is not between 0 and 1
        """
        if not 0 <= v <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        return v

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects
