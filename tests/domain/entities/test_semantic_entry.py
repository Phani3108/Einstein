"""Tests for the SemanticEntry domain entity."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import Relationship, SemanticEntry


def test_relationship_creation():
    """Test that a relationship can be created with valid data."""
    # Arrange
    relationship_id = uuid.uuid4()
    source_entity_id = uuid.uuid4()
    target_entity_id = uuid.uuid4()
    relationship_type = "mentions"
    strength = 0.8
    created_at = datetime.now()

    # Act
    relationship = Relationship(
        id=relationship_id,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        relationship_type=relationship_type,
        strength=strength,
        created_at=created_at,
    )

    # Assert
    assert relationship.id == relationship_id
    assert relationship.source_entity_id == source_entity_id
    assert relationship.target_entity_id == target_entity_id
    assert relationship.relationship_type == relationship_type
    assert relationship.strength == strength
    assert relationship.created_at == created_at


def test_relationship_strength_validation():
    """Test that relationship strength is validated to be between 0 and 1."""
    # Arrange
    relationship_id = uuid.uuid4()
    source_entity_id = uuid.uuid4()
    target_entity_id = uuid.uuid4()

    # Act & Assert - Test with strength < 0
    with pytest.raises(ValidationError) as exc_info:
        Relationship(
            id=relationship_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type="mentions",
            strength=-0.1,
        )

    assert "strength" in str(exc_info.value)

    # Act & Assert - Test with strength > 1
    with pytest.raises(ValidationError) as exc_info:
        Relationship(
            id=relationship_id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type="mentions",
            strength=1.1,
        )

    assert "strength" in str(exc_info.value)


def test_semantic_entry_creation():
    """Test that a semantic entry can be created with valid data."""
    # Arrange
    entry_id = uuid.uuid4()
    thought_id = uuid.uuid4()
    entity_type = EntityType.PERSON
    entity_value = "John Doe"
    confidence = 0.95
    context = "I met with John Doe yesterday"
    embedding = [0.1, 0.2, 0.3, 0.4]
    extracted_at = datetime.now()

    # Act
    semantic_entry = SemanticEntry(
        id=entry_id,
        thought_id=thought_id,
        entity_type=entity_type,
        entity_value=entity_value,
        confidence=confidence,
        context=context,
        embedding=embedding,
        extracted_at=extracted_at,
    )

    # Assert
    assert semantic_entry.id == entry_id
    assert semantic_entry.thought_id == thought_id
    assert semantic_entry.entity_type == entity_type
    assert semantic_entry.entity_value == entity_value
    assert semantic_entry.confidence == confidence
    assert semantic_entry.context == context
    assert semantic_entry.embedding == embedding
    assert semantic_entry.extracted_at == extracted_at
    assert semantic_entry.relationships == []


def test_semantic_entry_with_relationships():
    """Test that a semantic entry can be created with relationships."""
    # Arrange
    entry_id = uuid.uuid4()
    thought_id = uuid.uuid4()

    relationship = Relationship(
        id=uuid.uuid4(),
        source_entity_id=entry_id,
        target_entity_id=uuid.uuid4(),
        relationship_type="mentions",
        strength=0.8,
    )

    # Act
    semantic_entry = SemanticEntry(
        id=entry_id,
        thought_id=thought_id,
        entity_type=EntityType.PERSON,
        entity_value="John Doe",
        confidence=0.95,
        context="I met with John Doe yesterday",
        relationships=[relationship],
    )

    # Assert
    assert len(semantic_entry.relationships) == 1
    assert semantic_entry.relationships[0] == relationship


def test_semantic_entry_empty_entity_value():
    """Test that a semantic entry cannot be created with an empty entity value."""
    # Arrange
    entry_id = uuid.uuid4()
    thought_id = uuid.uuid4()

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        SemanticEntry(
            id=entry_id,
            thought_id=thought_id,
            entity_type=EntityType.PERSON,
            entity_value="",
            confidence=0.95,
            context="Empty entity value",
        )

    assert "Entity value cannot be empty" in str(exc_info.value)


def test_semantic_entry_confidence_validation():
    """Test that confidence is validated to be between 0 and 1."""
    # Arrange
    entry_id = uuid.uuid4()
    thought_id = uuid.uuid4()

    # Act & Assert - Test with confidence < 0
    with pytest.raises(ValidationError) as exc_info:
        SemanticEntry(
            id=entry_id,
            thought_id=thought_id,
            entity_type=EntityType.PERSON,
            entity_value="John Doe",
            confidence=-0.1,
            context="Test context",
        )

    assert "Confidence must be between 0 and 1" in str(exc_info.value)

    # Act & Assert - Test with confidence > 1
    with pytest.raises(ValidationError) as exc_info:
        SemanticEntry(
            id=entry_id,
            thought_id=thought_id,
            entity_type=EntityType.PERSON,
            entity_value="John Doe",
            confidence=1.1,
            context="Test context",
        )

    assert "Confidence must be between 0 and 1" in str(exc_info.value)
