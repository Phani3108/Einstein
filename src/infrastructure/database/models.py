"""SQLAlchemy models for the Personal Semantic Engine."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import Relationship as DomainRelationship
from src.domain.entities.semantic_entry import SemanticEntry as DomainSemanticEntry
from src.domain.entities.thought import GeoLocation
from src.domain.entities.thought import Thought as DomainThought
from src.domain.entities.thought import ThoughtMetadata, WeatherData
from src.domain.entities.user import User as DomainUser

Base = declarative_base()


class User(Base):
    """SQLAlchemy model for users."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_login = Column(DateTime, nullable=True)

    thoughts = relationship(
        "Thought", back_populates="user", cascade="all, delete-orphan"
    )

    def to_domain(self) -> DomainUser:
        """Convert to domain entity.

        Returns:
            Domain user entity
        """
        return DomainUser(
            id=self.id,
            email=self.email,
            hashed_password=self.hashed_password,
            is_active=self.is_active,
            is_admin=self.is_admin,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_login=self.last_login,
        )

    @classmethod
    def from_domain(cls, user: DomainUser) -> "User":
        """Create from domain entity.

        Args:
            user: Domain user entity

        Returns:
            SQLAlchemy user model
        """
        return cls(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        )


class Thought(Base):
    """SQLAlchemy model for thoughts."""

    __tablename__ = "thoughts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    thought_metadata = Column(
        JSONB, default={}
    )  # Renamed from metadata to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="thoughts")
    semantic_entries = relationship(
        "SemanticEntry", back_populates="thought", cascade="all, delete-orphan"
    )

    def to_domain(self) -> DomainThought:
        """Convert to domain entity.

        Returns:
            Domain thought entity
        """
        metadata_dict = self.thought_metadata or {}

        # Process location data if present
        location = None
        if metadata_dict.get("location"):
            loc_data = metadata_dict["location"]
            location = GeoLocation(
                latitude=loc_data.get("latitude"),
                longitude=loc_data.get("longitude"),
                name=loc_data.get("name"),
            )

        # Process weather data if present
        weather = None
        if metadata_dict.get("weather"):
            weather_data = metadata_dict["weather"]
            weather = WeatherData(
                temperature=weather_data.get("temperature"),
                condition=weather_data.get("condition"),
                humidity=weather_data.get("humidity"),
            )

        # Create metadata object
        metadata = ThoughtMetadata(
            location=location,
            weather=weather,
            mood=metadata_dict.get("mood"),
            tags=metadata_dict.get("tags", []),
            custom=metadata_dict.get("custom", {}),
        )

        # Convert semantic entries
        semantic_entries = [entry.to_domain() for entry in self.semantic_entries]

        return DomainThought(
            id=self.id,
            user_id=self.user_id,
            content=self.content,
            timestamp=self.timestamp,
            metadata=metadata,
            semantic_entries=semantic_entries,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, thought: DomainThought) -> "Thought":
        """Create from domain entity.

        Args:
            thought: Domain thought entity

        Returns:
            SQLAlchemy thought model
        """
        # Convert metadata to dict for JSONB storage
        metadata_dict = {}

        if thought.metadata:
            if thought.metadata.location:
                metadata_dict["location"] = {
                    "latitude": thought.metadata.location.latitude,
                    "longitude": thought.metadata.location.longitude,
                    "name": thought.metadata.location.name,
                }

            if thought.metadata.weather:
                metadata_dict["weather"] = {
                    "temperature": thought.metadata.weather.temperature,
                    "condition": thought.metadata.weather.condition,
                    "humidity": thought.metadata.weather.humidity,
                }

            if thought.metadata.mood:
                metadata_dict["mood"] = thought.metadata.mood

            if thought.metadata.tags:
                metadata_dict["tags"] = thought.metadata.tags

            if thought.metadata.custom:
                metadata_dict["custom"] = thought.metadata.custom

        return cls(
            id=thought.id,
            user_id=thought.user_id,
            content=thought.content,
            timestamp=thought.timestamp,
            thought_metadata=metadata_dict,
            created_at=thought.created_at,
            updated_at=thought.updated_at,
        )


class SemanticEntry(Base):
    """SQLAlchemy model for semantic entries."""

    __tablename__ = "semantic_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thought_id = Column(UUID(as_uuid=True), ForeignKey("thoughts.id"), nullable=False)
    entity_type = Column(String, nullable=False)
    entity_value = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    context = Column(String, nullable=False)
    embedding = Column(ARRAY(Float), nullable=True)
    extracted_at = Column(DateTime, default=datetime.now)

    thought = relationship("Thought", back_populates="semantic_entries")
    relationships = relationship(
        "Relationship",
        primaryjoin="or_(SemanticEntry.id==Relationship.source_entity_id, "
        "SemanticEntry.id==Relationship.target_entity_id)",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> DomainSemanticEntry:
        """Convert to domain entity.

        Returns:
            Domain semantic entry entity
        """
        # Convert relationships
        domain_relationships = [
            rel.to_domain()
            for rel in self.relationships
            if rel.source_entity_id == self.id
        ]

        return DomainSemanticEntry(
            id=self.id,
            thought_id=self.thought_id,
            entity_type=EntityType(self.entity_type),
            entity_value=self.entity_value,
            confidence=self.confidence,
            context=self.context,
            relationships=domain_relationships,
            embedding=self.embedding,
            extracted_at=self.extracted_at,
        )

    @classmethod
    def from_domain(cls, entry: DomainSemanticEntry) -> "SemanticEntry":
        """Create from domain entity.

        Args:
            entry: Domain semantic entry entity

        Returns:
            SQLAlchemy semantic entry model
        """
        return cls(
            id=entry.id,
            thought_id=entry.thought_id,
            entity_type=entry.entity_type.value,
            entity_value=entry.entity_value,
            confidence=entry.confidence,
            context=entry.context,
            embedding=entry.embedding,
            extracted_at=entry.extracted_at,
        )


class Relationship(Base):
    """SQLAlchemy model for relationships between semantic entries."""

    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(
        UUID(as_uuid=True), ForeignKey("semantic_entries.id"), nullable=False
    )
    target_entity_id = Column(
        UUID(as_uuid=True), ForeignKey("semantic_entries.id"), nullable=False
    )
    relationship_type = Column(String, nullable=False)
    strength = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    source_entity = relationship("SemanticEntry", foreign_keys=[source_entity_id])
    target_entity = relationship("SemanticEntry", foreign_keys=[target_entity_id])

    def to_domain(self) -> DomainRelationship:
        """Convert to domain entity.

        Returns:
            Domain relationship entity
        """
        return DomainRelationship(
            id=self.id,
            source_entity_id=self.source_entity_id,
            target_entity_id=self.target_entity_id,
            relationship_type=self.relationship_type,
            strength=self.strength,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, relationship: DomainRelationship) -> "Relationship":
        """Create from domain entity.

        Args:
            relationship: Domain relationship entity

        Returns:
            SQLAlchemy relationship model
        """
        return cls(
            id=relationship.id,
            source_entity_id=relationship.source_entity_id,
            target_entity_id=relationship.target_entity_id,
            relationship_type=relationship.relationship_type,
            strength=relationship.strength,
            created_at=relationship.created_at,
        )
