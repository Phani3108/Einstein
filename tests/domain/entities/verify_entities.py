"""Verify that domain entities are working correctly."""

import os
import sys
import uuid
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import (
    DateRange,
    EntityFilter,
    Pagination,
    SearchQuery,
    SortOptions,
)
from src.domain.entities.semantic_entry import Relationship, SemanticEntry
from src.domain.entities.thought import (
    GeoLocation,
    Thought,
    ThoughtMetadata,
    WeatherData,
)
from src.domain.entities.user import User


def verify_thought():
    """Verify that Thought entity works correctly."""
    print("Verifying Thought entity...")

    # Create a thought with minimal data
    thought_id = uuid.uuid4()
    user_id = uuid.uuid4()
    content = "This is a test thought"

    thought = Thought(
        id=thought_id,
        user_id=user_id,
        content=content,
    )

    assert thought.id == thought_id
    assert thought.user_id == user_id
    assert thought.content == content
    assert isinstance(thought.metadata, ThoughtMetadata)
    assert thought.semantic_entries == []

    # Create a thought with metadata
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

    thought = Thought(
        id=thought_id,
        user_id=user_id,
        content=content,
        metadata=metadata,
    )

    assert thought.metadata.location == location
    assert thought.metadata.weather == weather
    assert thought.metadata.mood == "Happy"
    assert thought.metadata.tags == ["test", "metadata"]
    assert thought.metadata.custom == {"key1": "value1", "key2": "value2"}

    print("Thought entity verification successful!")


def verify_semantic_entry():
    """Verify that SemanticEntry entity works correctly."""
    print("Verifying SemanticEntry entity...")

    # Create a semantic entry with minimal data
    entry_id = uuid.uuid4()
    thought_id = uuid.uuid4()
    entity_type = EntityType.PERSON
    entity_value = "John Doe"
    confidence = 0.95
    context = "I met with John Doe yesterday"

    semantic_entry = SemanticEntry(
        id=entry_id,
        thought_id=thought_id,
        entity_type=entity_type,
        entity_value=entity_value,
        confidence=confidence,
        context=context,
    )

    assert semantic_entry.id == entry_id
    assert semantic_entry.thought_id == thought_id
    assert semantic_entry.entity_type == entity_type
    assert semantic_entry.entity_value == entity_value
    assert semantic_entry.confidence == confidence
    assert semantic_entry.context == context
    assert semantic_entry.relationships == []

    # Create a semantic entry with relationships
    relationship = Relationship(
        id=uuid.uuid4(),
        source_entity_id=entry_id,
        target_entity_id=uuid.uuid4(),
        relationship_type="mentions",
        strength=0.8,
    )

    semantic_entry = SemanticEntry(
        id=entry_id,
        thought_id=thought_id,
        entity_type=entity_type,
        entity_value=entity_value,
        confidence=confidence,
        context=context,
        relationships=[relationship],
    )

    assert len(semantic_entry.relationships) == 1
    assert semantic_entry.relationships[0] == relationship

    print("SemanticEntry entity verification successful!")


def verify_user():
    """Verify that User entity works correctly."""
    print("Verifying User entity...")

    # Create a user with minimal data
    user_id = uuid.uuid4()
    email = "test@example.com"
    hashed_password = "hashed_password_string"

    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
    )

    assert user.id == user_id
    assert user.email == email
    assert user.hashed_password == hashed_password
    assert user.is_active is True
    assert user.is_admin is False

    # Create a user with all data
    created_at = datetime.now()
    updated_at = datetime.now()
    last_login = datetime.now()

    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        is_active=False,
        is_admin=True,
        created_at=created_at,
        updated_at=updated_at,
        last_login=last_login,
    )

    assert user.is_active is False
    assert user.is_admin is True
    assert user.created_at == created_at
    assert user.updated_at == updated_at
    assert user.last_login == last_login

    print("User entity verification successful!")


def verify_search_query():
    """Verify that SearchQuery entity works correctly."""
    print("Verifying SearchQuery entity...")

    # Create a search query with minimal data
    query_text = "test query"
    user_id = "user123"

    search_query = SearchQuery(
        query_text=query_text,
        user_id=user_id,
    )

    assert search_query.query_text == query_text
    assert search_query.user_id == user_id
    assert search_query.date_range is None
    assert search_query.entity_filter is None
    assert isinstance(search_query.sort_options, SortOptions)
    assert isinstance(search_query.pagination, Pagination)
    assert search_query.include_raw_content is True
    assert search_query.highlight_matches is True

    # Create a search query with all data
    date_range = DateRange(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )

    entity_filter = EntityFilter(
        entity_types=[EntityType.PERSON, EntityType.LOCATION],
        entity_values=["John Doe", "San Francisco"],
    )

    sort_options = SortOptions(
        sort_by="date",
        sort_order="asc",
    )

    pagination = Pagination(
        page=2,
        page_size=20,
    )

    search_query = SearchQuery(
        query_text=query_text,
        user_id=user_id,
        date_range=date_range,
        entity_filter=entity_filter,
        sort_options=sort_options,
        pagination=pagination,
        include_raw_content=False,
        highlight_matches=False,
    )

    assert search_query.date_range == date_range
    assert search_query.entity_filter == entity_filter
    assert search_query.sort_options == sort_options
    assert search_query.pagination == pagination
    assert search_query.include_raw_content is False
    assert search_query.highlight_matches is False

    print("SearchQuery entity verification successful!")


if __name__ == "__main__":
    try:
        verify_thought()
        verify_semantic_entry()
        verify_user()
        verify_search_query()
        print("\nAll domain entities verified successfully!")
    except Exception as e:
        print(f"\nVerification failed: {e}")
        sys.exit(1)
