"""SQLAlchemy models for the Personal Semantic Engine."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

import sqlalchemy as sa
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Table, Text
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
from src.domain.entities.context_event import (
    ContextEvent as DomainContextEvent,
    Connection as DomainConnection,
    PersonProfile as DomainPersonProfile,
    Project as DomainProject,
    Commitment as DomainCommitment,
)

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


# =========================================================================
# Context Aggregation Engine Models (Phase 0)
# =========================================================================


class ContextEventModel(Base):
    """Every piece of context from any source becomes a ContextEvent."""

    __tablename__ = "context_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source = Column(String, nullable=False)  # notification, phone, calendar, email, manual_note
    source_id = Column(String, nullable=True)  # dedup key
    event_type = Column(String, nullable=False)  # message, call, meeting, note, notification
    content = Column(Text, nullable=True)
    structured_data = Column(JSONB, default={})
    timestamp = Column(DateTime, nullable=False)

    # Tier 0: on-device extraction
    extracted_entities = Column(JSONB, nullable=True)
    extracted_people = Column(ARRAY(String), default=[])

    # Tier 1: embedding (pgvector — stored as float array for now, pgvector later)
    embedding = Column(ARRAY(Float), nullable=True)

    # Tier 2: LLM enrichment
    enriched_data = Column(JSONB, nullable=True)
    topics = Column(ARRAY(String), default=[])
    action_items = Column(JSONB, nullable=True)

    # Processing timestamps
    tier0_at = Column(DateTime, nullable=True)
    tier1_at = Column(DateTime, nullable=True)
    tier2_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User")

    def to_domain(self) -> DomainContextEvent:
        return DomainContextEvent(
            id=self.id,
            user_id=self.user_id,
            source=self.source,
            source_id=self.source_id,
            event_type=self.event_type,
            content=self.content,
            structured_data=self.structured_data or {},
            timestamp=self.timestamp,
            extracted_entities=self.extracted_entities,
            extracted_people=self.extracted_people or [],
            enriched_data=self.enriched_data,
            topics=self.topics or [],
            action_items=self.action_items,
            tier0_at=self.tier0_at,
            tier1_at=self.tier1_at,
            tier2_at=self.tier2_at,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, event: DomainContextEvent) -> "ContextEventModel":
        return cls(
            id=event.id,
            user_id=event.user_id,
            source=event.source,
            source_id=event.source_id,
            event_type=event.event_type,
            content=event.content,
            structured_data=event.structured_data,
            timestamp=event.timestamp,
            extracted_entities=event.extracted_entities,
            extracted_people=event.extracted_people,
            enriched_data=event.enriched_data,
            topics=event.topics,
            action_items=event.action_items,
            tier0_at=event.tier0_at,
            tier1_at=event.tier1_at,
            tier2_at=event.tier2_at,
            created_at=event.created_at,
        )


class ConnectionModel(Base):
    """A discovered link between two context events."""

    __tablename__ = "connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_event_id = Column(UUID(as_uuid=True), ForeignKey("context_events.id"), nullable=False)
    target_event_id = Column(UUID(as_uuid=True), ForeignKey("context_events.id"), nullable=False)
    connection_type = Column(String, nullable=False)
    strength = Column(Float, nullable=False)
    evidence = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.now)
    method = Column(String, default="entity_match")
    last_confirmed_at = Column(DateTime, nullable=True)

    # Relationships
    source_event = relationship("ContextEventModel", foreign_keys=[source_event_id])
    target_event = relationship("ContextEventModel", foreign_keys=[target_event_id])

    def to_domain(self) -> DomainConnection:
        return DomainConnection(
            id=self.id,
            user_id=self.user_id,
            source_event_id=self.source_event_id,
            target_event_id=self.target_event_id,
            connection_type=self.connection_type,
            strength=self.strength,
            evidence=self.evidence,
            discovered_at=self.discovered_at,
            method=self.method,
        )

    @classmethod
    def from_domain(cls, conn: DomainConnection) -> "ConnectionModel":
        return cls(
            id=conn.id,
            user_id=conn.user_id,
            source_event_id=conn.source_event_id,
            target_event_id=conn.target_event_id,
            connection_type=conn.connection_type,
            strength=conn.strength,
            evidence=conn.evidence,
            discovered_at=conn.discovered_at,
            method=conn.method,
        )


class PersonProfileModel(Base):
    """A person in the user's context graph."""

    __tablename__ = "people"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    aliases = Column(ARRAY(String), default=[])
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    role = Column(String, nullable=True)
    organization = Column(String, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    interaction_count = Column(Integer, default=0)
    notes = Column(Text, default="")
    # Temporal memory (Phase 2)
    freshness_score = Column(Float, default=1.0, nullable=False)
    last_activity_at = Column(DateTime, nullable=True)
    dormancy_days = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")

    def to_domain(self) -> DomainPersonProfile:
        return DomainPersonProfile(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            aliases=self.aliases or [],
            phone=self.phone,
            email=self.email,
            role=self.role,
            organization=self.organization,
            last_seen=self.last_seen,
            interaction_count=self.interaction_count,
            notes=self.notes or "",
            freshness_score=self.freshness_score,
            last_activity_at=self.last_activity_at,
            dormancy_days=self.dormancy_days,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, person: DomainPersonProfile) -> "PersonProfileModel":
        return cls(
            id=person.id,
            user_id=person.user_id,
            name=person.name,
            aliases=person.aliases,
            phone=person.phone,
            email=person.email,
            role=person.role,
            organization=person.organization,
            last_seen=person.last_seen,
            interaction_count=person.interaction_count,
            notes=person.notes,
            freshness_score=person.freshness_score,
            last_activity_at=person.last_activity_at,
            dormancy_days=person.dormancy_days,
            created_at=person.created_at,
        )


class ProjectModel(Base):
    """A user-defined project."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    status = Column(String, default="active")
    deadline = Column(DateTime, nullable=True)
    # Temporal memory (Phase 2)
    last_activity_at = Column(DateTime, nullable=True)
    dormancy_days = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User")

    def to_domain(self) -> DomainProject:
        return DomainProject(
            id=self.id,
            user_id=self.user_id,
            title=self.title,
            description=self.description or "",
            status=self.status or "active",
            deadline=self.deadline,
            last_activity_at=self.last_activity_at,
            dormancy_days=self.dormancy_days,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, project: DomainProject) -> "ProjectModel":
        return cls(
            id=project.id,
            user_id=project.user_id,
            title=project.title,
            description=project.description,
            status=project.status,
            deadline=project.deadline,
            last_activity_at=project.last_activity_at,
            dormancy_days=project.dormancy_days,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class CommitmentModel(Base):
    """Tracked commitment extracted from context events."""

    __tablename__ = "commitments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("context_events.id"), nullable=False)
    person_id = Column(UUID(as_uuid=True), ForeignKey("people.id"), nullable=True)
    description = Column(Text, nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="open")  # open, fulfilled, overdue, cancelled
    fulfilled_event_id = Column(UUID(as_uuid=True), ForeignKey("context_events.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User")
    event = relationship("ContextEventModel", foreign_keys=[event_id])
    person = relationship("PersonProfileModel")

    def to_domain(self) -> DomainCommitment:
        return DomainCommitment(
            id=self.id,
            user_id=self.user_id,
            event_id=self.event_id,
            person_id=self.person_id,
            description=self.description,
            due_date=self.due_date,
            status=self.status,
            fulfilled_event_id=self.fulfilled_event_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, c: DomainCommitment) -> "CommitmentModel":
        return cls(
            id=c.id,
            user_id=c.user_id,
            event_id=c.event_id,
            person_id=c.person_id,
            description=c.description,
            due_date=c.due_date,
            status=c.status,
            fulfilled_event_id=c.fulfilled_event_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )


class ResurfacingLogModel(Base):
    """Log of items surfaced to the user (briefings, prep packs, suggestions)."""

    __tablename__ = "resurfacing_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(String(30), nullable=False)  # morning_briefing, meeting_prep, weekly_digest, suggestion
    payload = Column(JSON, nullable=True)
    delivered_at = Column(DateTime, default=datetime.now)
    seen_at = Column(DateTime, nullable=True)
    acted_on = Column(Boolean, default=False)

    user = relationship("User")


# =========================================================================
# Vault API Models
# =========================================================================


class VaultNoteModel(Base):
    __tablename__ = "vault_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    frontmatter = Column(JSONB, default={})
    outgoing_links = Column(JSONB, default=[])
    is_bookmarked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Index for user + bookmark queries
    __table_args__ = (
        Index("ix_vault_notes_user_bookmark", "user_id", "is_bookmarked"),
    )

    def to_domain(self):
        from src.domain.entities.vault import VaultNote
        return VaultNote(
            id=self.id, user_id=self.user_id, file_path=self.file_path,
            title=self.title, content=self.content or "",
            frontmatter=self.frontmatter or {},
            outgoing_links=self.outgoing_links or [],
            is_bookmarked=self.is_bookmarked or False,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, note):
        return cls(
            id=note.id, user_id=note.user_id, file_path=note.file_path,
            title=note.title, content=note.content,
            frontmatter=note.frontmatter,
            outgoing_links=note.outgoing_links,
            is_bookmarked=note.is_bookmarked,
            created_at=note.created_at, updated_at=note.updated_at,
        )


class VaultNoteVersionModel(Base):
    __tablename__ = "vault_note_versions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_id = Column(UUID(as_uuid=True), ForeignKey("vault_notes.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, default="")
    frontmatter = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.now)

    def to_domain(self):
        from src.domain.entities.vault import VaultNoteVersion
        return VaultNoteVersion(id=self.id, note_id=self.note_id, content=self.content or "", frontmatter=self.frontmatter or "{}", created_at=self.created_at)

    @classmethod
    def from_domain(cls, v):
        return cls(id=v.id, note_id=v.note_id, content=v.content, frontmatter=v.frontmatter, created_at=v.created_at)


class VaultDecisionModel(Base):
    __tablename__ = "vault_decisions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    reasoning = Column(Text, default="")
    alternatives = Column(Text, default="")
    status = Column(String, default="active")
    decided_at = Column(String, default="")
    revisit_date = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    def to_domain(self):
        from src.domain.entities.vault import VaultDecision
        return VaultDecision(id=self.id, user_id=self.user_id, title=self.title, description=self.description or "", reasoning=self.reasoning or "", alternatives=self.alternatives or "", status=self.status or "active", decided_at=self.decided_at or "", revisit_date=self.revisit_date, created_at=self.created_at)

    @classmethod
    def from_domain(cls, d):
        return cls(id=d.id, user_id=d.user_id, title=d.title, description=d.description, reasoning=d.reasoning, alternatives=d.alternatives, status=d.status, decided_at=d.decided_at, revisit_date=d.revisit_date, created_at=d.created_at)


class NoteAssociationModel(Base):
    __tablename__ = "note_associations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    note_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    object_type = Column(String, nullable=False)
    object_id = Column(UUID(as_uuid=True), nullable=False)
    relationship = Column(String, default="")
    confidence = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("ix_note_assoc_note", "note_id"),
        Index("ix_note_assoc_object", "object_type", "object_id"),
    )

    def to_domain(self):
        from src.domain.entities.vault import NoteAssociation
        return NoteAssociation(id=self.id, user_id=self.user_id, note_id=self.note_id, object_type=self.object_type, object_id=self.object_id, relationship=self.relationship or "", confidence=self.confidence or 0.5, created_at=self.created_at)

    @classmethod
    def from_domain(cls, a):
        return cls(id=a.id, user_id=a.user_id, note_id=a.note_id, object_type=a.object_type, object_id=a.object_id, relationship=a.relationship, confidence=a.confidence, created_at=a.created_at)


class NoteMetadataModel(Base):
    __tablename__ = "note_metadata"
    note_id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    lifecycle = Column(String, default="active")
    last_meaningful_edit = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0)
    importance_score = Column(Float, default=0.5)
    distilled_at = Column(DateTime, nullable=True)
    source_type = Column(String, default="manual")

    def to_domain(self):
        from src.domain.entities.vault import NoteMetadata
        return NoteMetadata(note_id=self.note_id, user_id=self.user_id, lifecycle=self.lifecycle or "active", last_meaningful_edit=self.last_meaningful_edit, view_count=self.view_count or 0, importance_score=self.importance_score or 0.5, distilled_at=self.distilled_at, source_type=self.source_type or "manual")

    @classmethod
    def from_domain(cls, m):
        return cls(note_id=m.note_id, user_id=m.user_id, lifecycle=m.lifecycle, last_meaningful_edit=m.last_meaningful_edit, view_count=m.view_count, importance_score=m.importance_score, distilled_at=m.distilled_at, source_type=m.source_type)


class ActionItemModel(Base):
    __tablename__ = "action_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    note_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    task = Column(Text, nullable=False)
    assignee = Column(String, nullable=True)
    deadline = Column(String, nullable=True)
    priority = Column(String, default="medium")
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.now)

    def to_domain(self):
        from src.domain.entities.vault import ActionItem
        return ActionItem(id=self.id, user_id=self.user_id, note_id=self.note_id, task=self.task, assignee=self.assignee, deadline=self.deadline, priority=self.priority or "medium", status=self.status or "pending", created_at=self.created_at)

    @classmethod
    def from_domain(cls, a):
        return cls(id=a.id, user_id=a.user_id, note_id=a.note_id, task=a.task, assignee=a.assignee, deadline=a.deadline, priority=a.priority, status=a.status, created_at=a.created_at)


class CalendarEventModel(Base):
    __tablename__ = "calendar_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    note_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False)
    event_date = Column(String, nullable=False)
    event_type = Column(String, default="reminder")
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    def to_domain(self):
        from src.domain.entities.vault import CalendarEvent
        return CalendarEvent(id=self.id, user_id=self.user_id, note_id=self.note_id, title=self.title, event_date=self.event_date, event_type=self.event_type or "reminder", description=self.description or "", created_at=self.created_at)

    @classmethod
    def from_domain(cls, e):
        return cls(id=e.id, user_id=e.user_id, note_id=e.note_id, title=e.title, event_date=e.event_date, event_type=e.event_type, description=e.description, created_at=e.created_at)


class VaultConfigModel(Base):
    __tablename__ = "vault_config"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(Text, default="")


# =========================================================================
# Integration Connector Models (Phase 1A)
# =========================================================================


class IntegrationCredentialModel(Base):
    """OAuth credentials and sync state for a third-party integration."""

    __tablename__ = "integration_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(ARRAY(String), default=[])
    integration_metadata = Column(JSONB, default={})
    last_sync_at = Column(DateTime, nullable=True)
    sync_cursor = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User")

    __table_args__ = (
        Index("ix_integration_credentials_user_id", "user_id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_integration_user_provider"),
    )


class ProjectEventLinkModel(Base):
    """Auto-linking between projects and context events."""

    __tablename__ = "project_event_links"

    project_id = Column(UUID(as_uuid=True), primary_key=True)
    event_id = Column(UUID(as_uuid=True), primary_key=True)
    confidence = Column(Float, default=0.5)
    method = Column(String(30), default="auto")
    created_at = Column(DateTime, default=datetime.now)


class ActionLogModel(Base):
    """Outbound action log for tracking actions taken via connectors."""

    __tablename__ = "action_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=True)
    params = Column(JSONB, nullable=False, default={})
    result = Column(JSONB, nullable=True)
    status = Column(String(20), default="pending")
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")


class AudioUploadModel(Base):
    """Audio file uploads for transcription processing."""

    __tablename__ = "audio_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(UUID(as_uuid=True), nullable=True)
    file_url = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
