"""Enums for the Personal Semantic Engine domain."""

from enum import Enum, auto


class EntityType(str, Enum):
    """Types of semantic entities that can be extracted from thoughts."""

    PERSON = "person"
    LOCATION = "location"
    DATE = "date"
    ACTIVITY = "activity"
    EMOTION = "emotion"
    ORGANIZATION = "organization"
    EVENT = "event"
