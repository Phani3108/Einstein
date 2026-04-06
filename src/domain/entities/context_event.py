"""Context event domain entity — the core unit of the context aggregation engine.

Every piece of context entering Einstein (notification, call, email, note, calendar event)
becomes a ContextEvent. Events are processed through three tiers:
  - Tier 0: On-device regex/NER (instant)
  - Tier 1: Cloud embeddings (seconds)
  - Tier 2: LLM enrichment (batched, minutes)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContextEvent(BaseModel):
    """A single unit of context from any source."""

    id: UUID
    user_id: UUID
    source: str  # 'notification', 'phone', 'calendar', 'email', 'manual_note', 'sms', 'whatsapp'
    source_id: Optional[str] = None  # dedup key from source system
    event_type: str  # 'message', 'call', 'meeting', 'email_received', 'note', 'notification'
    content: Optional[str] = None  # raw text content
    structured_data: Dict[str, Any] = Field(default_factory=dict)  # source-specific fields
    timestamp: datetime

    # Tier 0 results (on-device extraction)
    extracted_entities: Optional[Dict[str, Any]] = None
    extracted_people: List[str] = Field(default_factory=list)

    # Tier 1 results (embeddings — stored in DB, not in domain object)
    # embedding: handled at infrastructure level

    # Tier 2 results (LLM enrichment)
    enriched_data: Optional[Dict[str, Any]] = None
    topics: List[str] = Field(default_factory=list)
    action_items: Optional[Dict[str, Any]] = None

    # Processing timestamps
    tier0_at: Optional[datetime] = None
    tier1_at: Optional[datetime] = None
    tier2_at: Optional[datetime] = None

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True


class Connection(BaseModel):
    """A discovered link between two context events."""

    id: UUID
    user_id: UUID
    source_event_id: UUID
    target_event_id: UUID
    connection_type: str  # 'same_person', 'same_topic', 'follow_up', 'temporal', 'semantic_similar'
    strength: float  # 0-1
    evidence: Optional[str] = None  # human-readable reason
    discovered_at: datetime = Field(default_factory=datetime.now)
    method: str = "entity_match"  # 'entity_match', 'embedding_similarity', 'llm_inference', 'temporal_cluster'

    class Config:
        frozen = True


class PersonProfile(BaseModel):
    """A person in the user's context graph, auto-populated from events + contacts."""

    id: UUID
    user_id: UUID
    name: str
    aliases: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    last_seen: Optional[datetime] = None
    interaction_count: int = 0
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True


class Project(BaseModel):
    """A user-defined project that events can be linked to."""

    id: UUID
    user_id: UUID
    title: str
    description: str = ""
    status: str = "active"  # active, paused, completed, archived
    deadline: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        frozen = True
