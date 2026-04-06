"""Context ingestion and query API routes.

These endpoints handle the core data flow:
  - Mobile app pushes context events (notifications, calls, calendar, etc.)
  - Clients query events and connections
  - Sync endpoints for offline-first mobile
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.domain.entities.context_event import ContextEvent, PersonProfile, Project
from src.domain.entities.user import User


# ---- Request/Response Models ----

class ContextEventIn(BaseModel):
    """Incoming context event from mobile."""
    source: str
    source_id: Optional[str] = None
    event_type: str
    content: Optional[str] = None
    structured_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    extracted_entities: Optional[Dict[str, Any]] = None
    extracted_people: List[str] = Field(default_factory=list)
    tier0_at: Optional[datetime] = None


class IngestRequest(BaseModel):
    """Batch of context events from mobile."""
    events: List[ContextEventIn]


class IngestResponse(BaseModel):
    inserted: int
    total: int


class ContextEventOut(BaseModel):
    id: str
    source: str
    source_id: Optional[str]
    event_type: str
    content: Optional[str]
    structured_data: Dict[str, Any]
    timestamp: datetime
    extracted_people: List[str]
    topics: List[str]
    tier0_at: Optional[datetime]
    tier1_at: Optional[datetime]
    tier2_at: Optional[datetime]
    created_at: datetime


class ConnectionOut(BaseModel):
    id: str
    source_event_id: str
    target_event_id: str
    connection_type: str
    strength: float
    evidence: Optional[str]
    method: str
    discovered_at: datetime


class PersonIn(BaseModel):
    name: str
    aliases: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None


class PersonOut(BaseModel):
    id: str
    name: str
    aliases: List[str]
    phone: Optional[str]
    email: Optional[str]
    role: Optional[str]
    organization: Optional[str]
    last_seen: Optional[datetime]
    interaction_count: int
    created_at: datetime


class ProjectIn(BaseModel):
    title: str
    description: str = ""
    status: str = "active"
    deadline: Optional[datetime] = None


class ProjectOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    deadline: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SyncPullResponse(BaseModel):
    events: List[ContextEventOut]
    connections: List[ConnectionOut]
    server_time: datetime


# ---- Router Factory ----

def create_context_router(
    context_repo: ContextEventRepository,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/context", tags=["context"])

    async def get_user(user=Depends(auth_middleware.require_authentication)) -> User:
        return user

    # ---- Ingestion ----

    @router.post("/ingest", response_model=IngestResponse)
    async def ingest_events(req: IngestRequest, user: User = Depends(auth_middleware.require_authentication)):
        """Receive a batch of context events from mobile."""
        domain_events = []
        for ev in req.events:
            domain_events.append(ContextEvent(
                id=uuid.uuid4(),
                user_id=user.id,
                source=ev.source,
                source_id=ev.source_id,
                event_type=ev.event_type,
                content=ev.content,
                structured_data=ev.structured_data,
                timestamp=ev.timestamp,
                extracted_entities=ev.extracted_entities,
                extracted_people=ev.extracted_people,
                tier0_at=ev.tier0_at,
            ))
        inserted = await context_repo.ingest_batch(domain_events)
        return IngestResponse(inserted=inserted, total=len(req.events))

    # ---- Query ----

    @router.get("/events", response_model=List[ContextEventOut])
    async def get_events(
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = Query(default=50, le=200),
        offset: int = 0,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Query context events with filters."""
        events = await context_repo.get_events(
            user_id=user.id, source=source, since=since, until=until, limit=limit, offset=offset
        )
        return [
            ContextEventOut(
                id=str(e.id),
                source=e.source,
                source_id=e.source_id,
                event_type=e.event_type,
                content=e.content,
                structured_data=e.structured_data,
                timestamp=e.timestamp,
                extracted_people=e.extracted_people,
                topics=e.topics,
                tier0_at=e.tier0_at,
                tier1_at=e.tier1_at,
                tier2_at=e.tier2_at,
                created_at=e.created_at,
            )
            for e in events
        ]

    @router.get("/connections", response_model=List[ConnectionOut])
    async def get_connections(
        event_id: Optional[str] = None,
        limit: int = Query(default=50, le=200),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get connection graph."""
        eid = uuid.UUID(event_id) if event_id else None
        conns = await context_repo.get_connections(user_id=user.id, event_id=eid, limit=limit)
        return [
            ConnectionOut(
                id=str(c.id),
                source_event_id=str(c.source_event_id),
                target_event_id=str(c.target_event_id),
                connection_type=c.connection_type,
                strength=c.strength,
                evidence=c.evidence,
                method=c.method,
                discovered_at=c.discovered_at,
            )
            for c in conns
        ]

    @router.get("/timeline", response_model=List[ContextEventOut])
    async def get_timeline(
        limit: int = Query(default=50, le=200),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Unified timeline across all sources."""
        events = await context_repo.get_events(user_id=user.id, limit=limit)
        return [
            ContextEventOut(
                id=str(e.id),
                source=e.source,
                source_id=e.source_id,
                event_type=e.event_type,
                content=e.content,
                structured_data=e.structured_data,
                timestamp=e.timestamp,
                extracted_people=e.extracted_people,
                topics=e.topics,
                tier0_at=e.tier0_at,
                tier1_at=e.tier1_at,
                tier2_at=e.tier2_at,
                created_at=e.created_at,
            )
            for e in events
        ]

    # ---- People ----

    @router.post("/people", response_model=PersonOut)
    async def upsert_person(req: PersonIn, user: User = Depends(auth_middleware.require_authentication)):
        """Create or update a person."""
        person = PersonProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            name=req.name,
            aliases=req.aliases,
            phone=req.phone,
            email=req.email,
            role=req.role,
            organization=req.organization,
        )
        result = await context_repo.upsert_person(person)
        return PersonOut(
            id=str(result.id),
            name=result.name,
            aliases=result.aliases,
            phone=result.phone,
            email=result.email,
            role=result.role,
            organization=result.organization,
            last_seen=result.last_seen,
            interaction_count=result.interaction_count,
            created_at=result.created_at,
        )

    @router.get("/people", response_model=List[PersonOut])
    async def get_people(user: User = Depends(auth_middleware.require_authentication)):
        """Get all people."""
        people = await context_repo.get_people(user.id)
        return [
            PersonOut(
                id=str(p.id), name=p.name, aliases=p.aliases, phone=p.phone,
                email=p.email, role=p.role, organization=p.organization,
                last_seen=p.last_seen, interaction_count=p.interaction_count,
                created_at=p.created_at,
            )
            for p in people
        ]

    # ---- Projects ----

    @router.post("/projects", response_model=ProjectOut)
    async def create_project(req: ProjectIn, user: User = Depends(auth_middleware.require_authentication)):
        """Create a project."""
        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=req.title,
            description=req.description,
            status=req.status,
            deadline=req.deadline,
        )
        result = await context_repo.create_project(project)
        return ProjectOut(
            id=str(result.id), title=result.title, description=result.description,
            status=result.status, deadline=result.deadline,
            created_at=result.created_at, updated_at=result.updated_at,
        )

    @router.get("/projects", response_model=List[ProjectOut])
    async def get_projects(
        status: Optional[str] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get projects."""
        projects = await context_repo.get_projects(user.id, status=status)
        return [
            ProjectOut(
                id=str(p.id), title=p.title, description=p.description,
                status=p.status, deadline=p.deadline,
                created_at=p.created_at, updated_at=p.updated_at,
            )
            for p in projects
        ]

    # ---- Sync ----

    @router.get("/sync/pull", response_model=SyncPullResponse)
    async def sync_pull(
        since: Optional[datetime] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Pull new data since last sync."""
        events = await context_repo.get_events(user_id=user.id, since=since, limit=200)
        conns = await context_repo.get_connections(user_id=user.id, limit=200)
        return SyncPullResponse(
            events=[
                ContextEventOut(
                    id=str(e.id), source=e.source, source_id=e.source_id,
                    event_type=e.event_type, content=e.content,
                    structured_data=e.structured_data, timestamp=e.timestamp,
                    extracted_people=e.extracted_people, topics=e.topics,
                    tier0_at=e.tier0_at, tier1_at=e.tier1_at, tier2_at=e.tier2_at,
                    created_at=e.created_at,
                )
                for e in events
            ],
            connections=[
                ConnectionOut(
                    id=str(c.id), source_event_id=str(c.source_event_id),
                    target_event_id=str(c.target_event_id),
                    connection_type=c.connection_type, strength=c.strength,
                    evidence=c.evidence, method=c.method, discovered_at=c.discovered_at,
                )
                for c in conns
            ],
            server_time=datetime.now(),
        )

    return router
