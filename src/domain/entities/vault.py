"""Vault domain entities — notes, versions, metadata, action items, calendar events, decisions."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
import uuid as uuid_mod


class VaultNote(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    user_id: UUID
    file_path: str
    title: str
    content: str = ""
    frontmatter: Dict[str, Any] = {}
    outgoing_links: List[str] = []
    is_bookmarked: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class VaultNoteVersion(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    note_id: UUID
    content: str
    frontmatter: str = "{}"
    created_at: datetime = Field(default_factory=datetime.now)


class VaultDecision(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    user_id: UUID
    title: str
    description: str = ""
    reasoning: str = ""
    alternatives: str = ""
    status: str = "active"
    decided_at: str = ""
    revisit_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class NoteAssociation(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    user_id: UUID
    note_id: UUID
    object_type: str  # "project", "person", "decision"
    object_id: UUID
    relationship: str
    confidence: float = 0.5
    created_at: datetime = Field(default_factory=datetime.now)


class NoteMetadata(BaseModel, frozen=True):
    note_id: UUID
    user_id: UUID
    lifecycle: str = "active"
    last_meaningful_edit: Optional[datetime] = None
    view_count: int = 0
    importance_score: float = 0.5
    distilled_at: Optional[datetime] = None
    source_type: str = "manual"


class ActionItem(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    user_id: UUID
    note_id: UUID
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.now)


class CalendarEvent(BaseModel, frozen=True):
    id: UUID = Field(default_factory=uuid_mod.uuid4)
    user_id: UUID
    note_id: UUID
    title: str
    event_date: str
    event_type: str = "reminder"
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class VaultConfig(BaseModel, frozen=True):
    user_id: UUID
    key: str
    value: str
