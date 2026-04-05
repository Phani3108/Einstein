"""Domain entities for the Personal Semantic Engine.

This package contains the core domain entities that represent the business objects
of the application. These are pure Pydantic models with validation rules.
"""

from .enums import EntityType
from .search_query import DateRange, EntityFilter, Pagination, SearchQuery, SortOptions
from .search_result import SearchMatch, SearchResponse, SearchResult, SearchScore
from .semantic_entry import Relationship, SemanticEntry
from .thought import GeoLocation, Thought, ThoughtMetadata, WeatherData
from .user import User

__all__ = [
    "EntityType",
    "DateRange",
    "EntityFilter",
    "GeoLocation",
    "Pagination",
    "Relationship",
    "SearchMatch",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchScore",
    "SemanticEntry",
    "SortOptions",
    "Thought",
    "ThoughtMetadata",
    "User",
    "WeatherData",
]
