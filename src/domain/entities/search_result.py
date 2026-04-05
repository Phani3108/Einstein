"""Search result domain entity for the Personal Semantic Engine."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought


class SearchMatch(BaseModel):
    """A match found in search results."""

    field: str  # The field where the match was found (content, entity_value, etc.)
    text: str  # The matched text
    start_position: int  # Start position of the match
    end_position: int  # End position of the match
    highlight: str  # Highlighted version of the match


class SearchScore(BaseModel):
    """Detailed scoring information for a search result."""

    semantic_similarity: float = Field(ge=0.0, le=1.0)
    keyword_match: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """A search result containing a thought and its matching information."""

    thought: Thought
    matching_entities: List[SemanticEntry] = Field(default_factory=list)
    matches: List[SearchMatch] = Field(default_factory=list)
    score: SearchScore
    rank: int  # Position in the search results (1-based)

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects


class SearchResponse(BaseModel):
    """Response containing search results and metadata."""

    results: List[SearchResult] = Field(default_factory=list)
    total_count: int
    page: int
    page_size: int
    query_text: str
    search_time_ms: int
    suggestions: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects