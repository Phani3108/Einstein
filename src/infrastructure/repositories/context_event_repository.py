"""Repository for context events, connections, people, and projects."""

import uuid
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, desc, func, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.domain.entities.context_event import ContextEvent, Connection, PersonProfile, Project, Commitment
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    ContextEventModel,
    ConnectionModel,
    PersonProfileModel,
    ProjectModel,
    CommitmentModel,
    ResurfacingLogModel,
    IntegrationCredentialModel,
)


class ContextEventRepository:
    """PostgreSQL repository for context events and related entities."""

    def __init__(self, database: Database):
        self._database = database

    # ---- Context Events ----

    async def ingest_batch(self, events: List[ContextEvent]) -> int:
        """Insert a batch of context events, skipping duplicates on (user_id, source, source_id)."""
        inserted = 0
        async with self._database.session() as session:
            for event in events:
                model = ContextEventModel.from_domain(event)
                # Use upsert to handle dedup
                if event.source_id:
                    stmt = pg_insert(ContextEventModel).values(
                        id=model.id,
                        user_id=model.user_id,
                        source=model.source,
                        source_id=model.source_id,
                        event_type=model.event_type,
                        content=model.content,
                        structured_data=model.structured_data,
                        timestamp=model.timestamp,
                        extracted_entities=model.extracted_entities,
                        extracted_people=model.extracted_people,
                        tier0_at=model.tier0_at,
                        created_at=model.created_at,
                    ).on_conflict_do_nothing(
                        index_elements=["user_id", "source", "source_id"],
                    )
                    result = await session.execute(stmt)
                    if result.rowcount > 0:
                        inserted += 1
                else:
                    session.add(model)
                    inserted += 1
            await session.commit()
        return inserted

    async def get_events(
        self,
        user_id: UUID,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContextEvent]:
        """Query context events with filters."""
        async with self._database.session() as session:
            stmt = select(ContextEventModel).where(
                ContextEventModel.user_id == user_id
            )
            if source:
                stmt = stmt.where(ContextEventModel.source == source)
            if since:
                stmt = stmt.where(ContextEventModel.timestamp >= since)
            if until:
                stmt = stmt.where(ContextEventModel.timestamp <= until)
            stmt = stmt.order_by(desc(ContextEventModel.timestamp)).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def get_unprocessed(self, user_id: UUID, tier: int, limit: int = 50) -> List[ContextEvent]:
        """Get events that haven't been processed at a given tier."""
        async with self._database.session() as session:
            if tier == 1:
                col = ContextEventModel.tier1_at
            elif tier == 2:
                col = ContextEventModel.tier2_at
            else:
                col = ContextEventModel.tier0_at

            stmt = (
                select(ContextEventModel)
                .where(and_(ContextEventModel.user_id == user_id, col.is_(None)))
                .order_by(ContextEventModel.timestamp)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def update_tier1(self, event_id: UUID, embedding: List[float]) -> None:
        """Store Tier 1 embedding result."""
        async with self._database.session() as session:
            stmt = (
                update(ContextEventModel)
                .where(ContextEventModel.id == event_id)
                .values(embedding=embedding, tier1_at=datetime.now())
            )
            await session.execute(stmt)
            await session.commit()

    async def update_tier2(
        self, event_id: UUID, enriched_data: dict, topics: List[str], action_items: Optional[dict]
    ) -> None:
        """Store Tier 2 LLM enrichment result."""
        async with self._database.session() as session:
            stmt = (
                update(ContextEventModel)
                .where(ContextEventModel.id == event_id)
                .values(
                    enriched_data=enriched_data,
                    topics=topics,
                    action_items=action_items,
                    tier2_at=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def count_events(self, user_id: UUID, source: Optional[str] = None) -> int:
        """Count events for a user."""
        async with self._database.session() as session:
            stmt = select(func.count()).select_from(ContextEventModel).where(
                ContextEventModel.user_id == user_id
            )
            if source:
                stmt = stmt.where(ContextEventModel.source == source)
            result = await session.execute(stmt)
            return result.scalar() or 0

    # ---- Connections ----

    async def create_connection(self, conn: Connection) -> Connection:
        """Create a new connection between events."""
        async with self._database.session() as session:
            model = ConnectionModel.from_domain(conn)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_domain()

    async def get_connections(
        self,
        user_id: UUID,
        event_id: Optional[UUID] = None,
        limit: int = 50,
    ) -> List[Connection]:
        """Get connections, optionally filtered by a specific event."""
        async with self._database.session() as session:
            stmt = select(ConnectionModel).where(ConnectionModel.user_id == user_id)
            if event_id:
                stmt = stmt.where(
                    (ConnectionModel.source_event_id == event_id)
                    | (ConnectionModel.target_event_id == event_id)
                )
            stmt = stmt.order_by(desc(ConnectionModel.strength)).limit(limit)
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    # ---- People ----

    async def upsert_person(self, person: PersonProfile) -> PersonProfile:
        """Create or update a person profile."""
        async with self._database.session() as session:
            existing = await session.execute(
                select(PersonProfileModel).where(
                    and_(
                        PersonProfileModel.user_id == person.user_id,
                        PersonProfileModel.name == person.name,
                    )
                )
            )
            existing_model = existing.scalar_one_or_none()
            if existing_model:
                # Update existing
                existing_model.phone = person.phone or existing_model.phone
                existing_model.email = person.email or existing_model.email
                existing_model.role = person.role or existing_model.role
                existing_model.organization = person.organization or existing_model.organization
                existing_model.last_seen = person.last_seen or existing_model.last_seen
                existing_model.interaction_count = max(person.interaction_count, existing_model.interaction_count)
                if person.aliases:
                    existing_aliases = set(existing_model.aliases or [])
                    existing_aliases.update(person.aliases)
                    existing_model.aliases = list(existing_aliases)
                await session.commit()
                await session.refresh(existing_model)
                return existing_model.to_domain()
            else:
                model = PersonProfileModel.from_domain(person)
                session.add(model)
                await session.commit()
                await session.refresh(model)
                return model.to_domain()

    async def get_people(self, user_id: UUID, limit: int = 100) -> List[PersonProfile]:
        """Get all people for a user."""
        async with self._database.session() as session:
            stmt = (
                select(PersonProfileModel)
                .where(PersonProfileModel.user_id == user_id)
                .order_by(desc(PersonProfileModel.interaction_count))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    # ---- Projects ----

    async def create_project(self, project: Project) -> Project:
        """Create a new project."""
        async with self._database.session() as session:
            model = ProjectModel.from_domain(project)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_domain()

    async def get_projects(self, user_id: UUID, status: Optional[str] = None) -> List[Project]:
        """Get projects for a user."""
        async with self._database.session() as session:
            stmt = select(ProjectModel).where(ProjectModel.user_id == user_id)
            if status:
                stmt = stmt.where(ProjectModel.status == status)
            stmt = stmt.order_by(desc(ProjectModel.updated_at))
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    # ---- Commitments ----

    async def create_commitment(self, commitment: Commitment) -> Commitment:
        """Create a new commitment."""
        async with self._database.session() as session:
            model = CommitmentModel.from_domain(commitment)
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.to_domain()

    async def get_commitments(
        self,
        user_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Commitment]:
        """Get commitments for a user."""
        async with self._database.session() as session:
            stmt = select(CommitmentModel).where(CommitmentModel.user_id == user_id)
            if status:
                stmt = stmt.where(CommitmentModel.status == status)
            stmt = stmt.order_by(desc(CommitmentModel.created_at)).limit(limit)
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def update_commitment_status(self, commitment_id: UUID, status: str, fulfilled_event_id: Optional[UUID] = None) -> None:
        """Update a commitment's status."""
        async with self._database.session() as session:
            values = {"status": status, "updated_at": datetime.now()}
            if fulfilled_event_id:
                values["fulfilled_event_id"] = fulfilled_event_id
            stmt = (
                update(CommitmentModel)
                .where(CommitmentModel.id == commitment_id)
                .values(**values)
            )
            await session.execute(stmt)
            await session.commit()

    # ---- Temporal Memory ----

    async def get_dormant_people(self, user_id: UUID, min_days: int = 21, limit: int = 20) -> List[PersonProfile]:
        """Get people who haven't been interacted with recently."""
        async with self._database.session() as session:
            stmt = (
                select(PersonProfileModel)
                .where(
                    and_(
                        PersonProfileModel.user_id == user_id,
                        PersonProfileModel.dormancy_days >= min_days,
                    )
                )
                .order_by(desc(PersonProfileModel.dormancy_days))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def get_dormant_projects(self, user_id: UUID, min_days: int = 14, limit: int = 20) -> List[Project]:
        """Get active projects that haven't had activity recently."""
        async with self._database.session() as session:
            stmt = (
                select(ProjectModel)
                .where(
                    and_(
                        ProjectModel.user_id == user_id,
                        ProjectModel.status == "active",
                        ProjectModel.dormancy_days >= min_days,
                    )
                )
                .order_by(desc(ProjectModel.dormancy_days))
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def update_person_activity(self, user_id: UUID, person_name: str) -> None:
        """Update last_activity_at for a person (called when they're mentioned in a new event)."""
        async with self._database.session() as session:
            stmt = (
                update(PersonProfileModel)
                .where(
                    and_(
                        PersonProfileModel.user_id == user_id,
                        PersonProfileModel.name == person_name,
                    )
                )
                .values(
                    last_activity_at=datetime.now(),
                    interaction_count=PersonProfileModel.interaction_count + 1,
                    last_seen=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def update_project_activity(self, project_id: UUID) -> None:
        """Update last_activity_at for a project."""
        async with self._database.session() as session:
            stmt = (
                update(ProjectModel)
                .where(ProjectModel.id == project_id)
                .values(last_activity_at=datetime.now(), updated_at=datetime.now())
            )
            await session.execute(stmt)
            await session.commit()

    # ── Integration credential helpers ──────────────────────────

    async def get_integration_credentials(self, user_id: UUID) -> list[dict]:
        """Return all integration credentials for a user."""
        async with self._database.session() as session:
            result = await session.execute(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.user_id == user_id
                )
            )
            rows = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "provider": r.provider,
                    "is_active": r.is_active,
                    "last_sync_at": r.last_sync_at.isoformat() if r.last_sync_at else None,
                    "scopes": r.scopes or [],
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    async def get_integration_credential(self, user_id: UUID, provider: str) -> dict | None:
        """Return a single credential by user+provider, or None."""
        async with self._database.session() as session:
            result = await session.execute(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.user_id == user_id,
                    IntegrationCredentialModel.provider == provider,
                )
            )
            r = result.scalar_one_or_none()
            if not r:
                return None
            return {
                "id": str(r.id),
                "provider": r.provider,
                "access_token": r.access_token,
                "refresh_token": r.refresh_token,
                "token_expiry": r.token_expiry.isoformat() if r.token_expiry else None,
                "is_active": r.is_active,
                "last_sync_at": r.last_sync_at.isoformat() if r.last_sync_at else None,
                "scopes": r.scopes or [],
                "integration_metadata": r.integration_metadata or {},
                "sync_cursor": r.sync_cursor,
            }

    async def upsert_integration_credential(
        self,
        user_id: UUID,
        provider: str,
        access_token: str,
        refresh_token: str | None = None,
        token_expiry: datetime | None = None,
        scopes: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Insert or update an integration credential."""
        async with self._database.session() as session:
            existing = await session.execute(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.user_id == user_id,
                    IntegrationCredentialModel.provider == provider,
                )
            )
            row = existing.scalar_one_or_none()
            if row:
                row.access_token = access_token
                if refresh_token is not None:
                    row.refresh_token = refresh_token
                if token_expiry is not None:
                    row.token_expiry = token_expiry
                if scopes is not None:
                    row.scopes = scopes
                if metadata is not None:
                    row.integration_metadata = metadata
                row.is_active = True
                row.updated_at = datetime.now()
            else:
                session.add(IntegrationCredentialModel(
                    user_id=user_id,
                    provider=provider,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expiry=token_expiry,
                    scopes=scopes or [],
                    integration_metadata=metadata or {},
                    is_active=True,
                ))
            await session.commit()

    async def deactivate_integration(self, user_id: UUID, provider: str) -> None:
        """Soft-delete: set is_active=False."""
        async with self._database.session() as session:
            result = await session.execute(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.user_id == user_id,
                    IntegrationCredentialModel.provider == provider,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.is_active = False
                row.updated_at = datetime.now()
                await session.commit()

    async def update_sync_cursor(
        self,
        user_id: UUID,
        provider: str,
        cursor: str | None,
        last_sync_at: datetime | None = None,
    ) -> None:
        """Update the sync cursor and last_sync_at for an integration."""
        async with self._database.session() as session:
            result = await session.execute(
                select(IntegrationCredentialModel).where(
                    IntegrationCredentialModel.user_id == user_id,
                    IntegrationCredentialModel.provider == provider,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.sync_cursor = cursor
                row.last_sync_at = last_sync_at or datetime.now()
                row.updated_at = datetime.now()
                await session.commit()
