"""Tests for the Thought domain entity."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.entities.thought import (
    GeoLocation,
    Thought,
    ThoughtMetadata,
    WeatherData,
)


def test_thought_creation():
    """Test that a thought can be created with valid data."""
    # Arrange
    thought_id = uuid.uuid4()
    user_id = uuid.uuid4()
    content = "This is a test thought"
    timestamp = datetime.now()

    # Act
    thought = Thought(
        id=thought_id,
        user_id=user_id,
        content=content,
        timestamp=timestamp,
    )

    # Assert
    assert thought.id == thought_id
    assert thought.user_id == user_id
    assert thought.content == content
    assert thought.timestamp == timestamp
    assert isinstance(thought.metadata, ThoughtMetadata)
    assert thought.semantic_entries == []


def test_thought_with_metadata():
    """Test that a thought can be created with metadata."""
    # Arrange
    thought_id = uuid.uuid4()
    user_id = uuid.uuid4()
    content = "This is a test thought with metadata"

    location = GeoLocation(
        latitude=37.7749,
        longitude=-122.4194,
        name="San Francisco",
    )

    weather = WeatherData(
        temperature=22.5,
        condition="Sunny",
        humidity=65.0,
    )

    metadata = ThoughtMetadata(
        location=location,
        weather=weather,
        mood="Happy",
        tags=["test", "metadata"],
        custom={"key1": "value1", "key2": "value2"},
    )

    # Act
    thought = Thought(
        id=thought_id,
        user_id=user_id,
        content=content,
        metadata=metadata,
    )

    # Assert
    assert thought.metadata.location == location
    assert thought.metadata.weather == weather
    assert thought.metadata.mood == "Happy"
    assert thought.metadata.tags == ["test", "metadata"]
    assert thought.metadata.custom == {"key1": "value1", "key2": "value2"}


def test_thought_empty_content():
    """Test that a thought cannot be created with empty content."""
    # Arrange
    thought_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        Thought(
            id=thought_id,
            user_id=user_id,
            content="",
        )

    assert "Thought content cannot be empty" in str(exc_info.value)
