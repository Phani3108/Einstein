"""Unit tests for ContextEventRepository with mocked database layer."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.entities.context_event import (
    Connection,
    ContextEvent,
    PersonProfile,
    Project,
)
from src.infrastructure.repositories.context_event_repository import ContextEventRepository


# ---- Helpers ----


def _make_event(user_id=None, source="notification", source_id=None, **kwargs):
    """Create a ContextEvent with sensible defaults."""
    return ContextEvent(
        id=uuid4(),
        user_id=user_id or uuid4(),
        source=source,
        source_id=source_id,
        event_type=kwargs.get("event_type", "message"),
        content=kwargs.get("content", "test event content"),
        structured_data=kwargs.get("structured_data", {}),
        timestamp=kwargs.get("timestamp", datetime.now()),
        extracted_entities=kwargs.get("extracted_entities", None),
        extracted_people=kwargs.get("extracted_people", []),
        tier0_at=kwargs.get("tier0_at", None),
        tier1_at=kwargs.get("tier1_at", None),
        tier2_at=kwargs.get("tier2_at", None),
        created_at=kwargs.get("created_at", datetime.now()),
    )


def _make_connection(user_id=None, **kwargs):
    """Create a Connection with sensible defaults."""
    return Connection(
        id=uuid4(),
        user_id=user_id or uuid4(),
        source_event_id=kwargs.get("source_event_id", uuid4()),
        target_event_id=kwargs.get("target_event_id", uuid4()),
        connection_type=kwargs.get("connection_type", "same_topic"),
        strength=kwargs.get("strength", 0.8),
        evidence=kwargs.get("evidence", "shared entity"),
        method=kwargs.get("method", "entity_match"),
        discovered_at=kwargs.get("discovered_at", datetime.now()),
    )


def _make_person(user_id=None, **kwargs):
    """Create a PersonProfile with sensible defaults."""
    return PersonProfile(
        id=uuid4(),
        user_id=user_id or uuid4(),
        name=kwargs.get("name", "Alice Smith"),
        aliases=kwargs.get("aliases", []),
        phone=kwargs.get("phone", None),
        email=kwargs.get("email", None),
        role=kwargs.get("role", None),
        organization=kwargs.get("organization", None),
        last_seen=kwargs.get("last_seen", None),
        interaction_count=kwargs.get("interaction_count", 0),
        created_at=kwargs.get("created_at", datetime.now()),
    )


def _make_project(user_id=None, **kwargs):
    """Create a Project with sensible defaults."""
    return Project(
        id=uuid4(),
        user_id=user_id or uuid4(),
        title=kwargs.get("title", "Project Alpha"),
        description=kwargs.get("description", "A test project"),
        status=kwargs.get("status", "active"),
        deadline=kwargs.get("deadline", None),
        created_at=kwargs.get("created_at", datetime.now()),
        updated_at=kwargs.get("updated_at", datetime.now()),
    )


# ---- Fixtures ----


@pytest.fixture
def mock_session():
    """Create a mock async session that supports context-manager protocol."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_database(mock_session):
    """Create a mock Database whose session() returns an async context manager."""
    database = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    database.session.return_value = ctx
    return database


@pytest.fixture
def repo(mock_database):
    """Create a ContextEventRepository with a mocked database."""
    return ContextEventRepository(mock_database)


# ======================================================================
# Context Events — ingest_batch
# ======================================================================


class TestIngestBatch:
    """Tests for ContextEventRepository.ingest_batch."""

    async def test_ingest_batch_inserts_events_with_source_id(self, repo, mock_session):
        """Events with source_id use upsert (pg_insert + on_conflict_do_nothing)."""
        user_id = uuid4()
        events = [
            _make_event(user_id=user_id, source_id="notif-1"),
            _make_event(user_id=user_id, source_id="notif-2"),
        ]

        # Simulate both rows inserted (rowcount > 0)
        result_mock = MagicMock()
        result_mock.rowcount = 1
        mock_session.execute.return_value = result_mock

        inserted = await repo.ingest_batch(events)

        assert inserted == 2
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_awaited_once()

    async def test_ingest_batch_dedup_skips_duplicates(self, repo, mock_session):
        """When on_conflict_do_nothing fires, rowcount == 0 — event is not counted."""
        user_id = uuid4()
        events = [
            _make_event(user_id=user_id, source_id="dup-1"),
            _make_event(user_id=user_id, source_id="dup-2"),
        ]

        # First insert succeeds, second is a duplicate
        result_ok = MagicMock(rowcount=1)
        result_dup = MagicMock(rowcount=0)
        mock_session.execute.side_effect = [result_ok, result_dup]

        inserted = await repo.ingest_batch(events)

        assert inserted == 1

    async def test_ingest_batch_without_source_id_uses_session_add(self, repo, mock_session):
        """Events without source_id skip upsert and use session.add directly."""
        user_id = uuid4()
        events = [
            _make_event(user_id=user_id, source_id=None),
        ]

        inserted = await repo.ingest_batch(events)

        assert inserted == 1
        mock_session.add.assert_called_once()
        # No execute call — session.add was used instead
        mock_session.execute.assert_not_awaited()

    async def test_ingest_batch_empty_list(self, repo, mock_session):
        """An empty list should return 0 inserted and still commit."""
        inserted = await repo.ingest_batch([])

        assert inserted == 0
        mock_session.commit.assert_awaited_once()

    async def test_ingest_batch_mixed_source_ids(self, repo, mock_session):
        """Mix of events with and without source_id in one batch."""
        user_id = uuid4()
        events = [
            _make_event(user_id=user_id, source_id="src-1"),
            _make_event(user_id=user_id, source_id=None),
            _make_event(user_id=user_id, source_id="src-2"),
        ]

        result_mock = MagicMock(rowcount=1)
        mock_session.execute.return_value = result_mock

        inserted = await repo.ingest_batch(events)

        assert inserted == 3
        # Two execute calls for events with source_id, one add for the one without
        assert mock_session.execute.call_count == 2
        assert mock_session.add.call_count == 1


# ======================================================================
# Context Events — get_events
# ======================================================================


class TestGetEvents:
    """Tests for ContextEventRepository.get_events."""

    async def test_get_events_basic(self, repo, mock_session):
        """Basic call with only user_id returns domain objects."""
        user_id = uuid4()
        mock_model = MagicMock()
        mock_model.to_domain.return_value = _make_event(user_id=user_id)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [mock_model]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_events(user_id=user_id)

        assert len(events) == 1
        mock_model.to_domain.assert_called_once()
        mock_session.execute.assert_awaited_once()

    async def test_get_events_returns_empty_list(self, repo, mock_session):
        """When no events match, return an empty list."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_events(user_id=uuid4())

        assert events == []

    async def test_get_events_with_all_filters(self, repo, mock_session):
        """Passing source, since, until, limit, offset should not raise."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_events(
            user_id=uuid4(),
            source="calendar",
            since=datetime.now() - timedelta(days=7),
            until=datetime.now(),
            limit=10,
            offset=5,
        )

        assert events == []
        mock_session.execute.assert_awaited_once()


# ======================================================================
# Context Events — get_unprocessed
# ======================================================================


class TestGetUnprocessed:
    """Tests for ContextEventRepository.get_unprocessed."""

    async def test_get_unprocessed_tier1(self, repo, mock_session):
        """Tier 1 unprocessed events are those where tier1_at is None."""
        user_id = uuid4()
        mock_model = MagicMock()
        mock_model.to_domain.return_value = _make_event(user_id=user_id, tier1_at=None)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [mock_model]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_unprocessed(user_id=user_id, tier=1, limit=10)

        assert len(events) == 1
        mock_session.execute.assert_awaited_once()

    async def test_get_unprocessed_tier2(self, repo, mock_session):
        """Tier 2 unprocessed events are those where tier2_at is None."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_unprocessed(user_id=uuid4(), tier=2)

        assert events == []

    async def test_get_unprocessed_tier0_fallback(self, repo, mock_session):
        """Unknown tier values fall through to tier0_at column."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        events = await repo.get_unprocessed(user_id=uuid4(), tier=99)

        assert events == []


# ======================================================================
# Context Events — update_tier1 / update_tier2
# ======================================================================


class TestUpdateTiers:
    """Tests for update_tier1 and update_tier2."""

    async def test_update_tier1_stores_embedding(self, repo, mock_session):
        """update_tier1 should execute an UPDATE and commit."""
        event_id = uuid4()
        embedding = [0.1, 0.2, 0.3]

        await repo.update_tier1(event_id, embedding)

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_update_tier2_stores_enrichment(self, repo, mock_session):
        """update_tier2 should execute an UPDATE and commit."""
        event_id = uuid4()

        await repo.update_tier2(
            event_id,
            enriched_data={"summary": "Important meeting"},
            topics=["meeting", "quarterly-review"],
            action_items={"follow_up": True},
        )

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()

    async def test_update_tier2_with_none_action_items(self, repo, mock_session):
        """update_tier2 with action_items=None should still succeed."""
        event_id = uuid4()

        await repo.update_tier2(
            event_id,
            enriched_data={"note": "casual"},
            topics=["chat"],
            action_items=None,
        )

        mock_session.execute.assert_awaited_once()
        mock_session.commit.assert_awaited_once()


# ======================================================================
# Context Events — count_events
# ======================================================================


class TestCountEvents:
    """Tests for ContextEventRepository.count_events."""

    async def test_count_events_returns_count(self, repo, mock_session):
        """count_events should return the scalar result."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = 42
        mock_session.execute.return_value = result_mock

        count = await repo.count_events(user_id=uuid4())

        assert count == 42

    async def test_count_events_with_source_filter(self, repo, mock_session):
        """count_events with source filter should still work."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = 5
        mock_session.execute.return_value = result_mock

        count = await repo.count_events(user_id=uuid4(), source="email")

        assert count == 5

    async def test_count_events_returns_zero_when_none(self, repo, mock_session):
        """When scalar() returns None, count should default to 0."""
        result_mock = MagicMock()
        result_mock.scalar.return_value = None
        mock_session.execute.return_value = result_mock

        count = await repo.count_events(user_id=uuid4())

        assert count == 0


# ======================================================================
# Connections
# ======================================================================


class TestConnections:
    """Tests for create_connection and get_connections."""

    async def test_create_connection(self, repo, mock_session):
        """create_connection should add, commit, refresh, and return domain object."""
        user_id = uuid4()
        conn = _make_connection(user_id=user_id)

        mock_model = MagicMock()
        mock_model.to_domain.return_value = conn

        # Patch from_domain to return a mock model
        with patch(
            "src.infrastructure.repositories.context_event_repository.ConnectionModel"
        ) as MockModel:
            MockModel.from_domain.return_value = mock_model
            mock_session.refresh = AsyncMock(return_value=None)

            result = await repo.create_connection(conn)

        assert result.id == conn.id
        mock_session.add.assert_called_once_with(mock_model)
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once_with(mock_model)

    async def test_get_connections_without_event_filter(self, repo, mock_session):
        """get_connections with no event_id returns all user connections."""
        user_id = uuid4()
        mock_model = MagicMock()
        mock_model.to_domain.return_value = _make_connection(user_id=user_id)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [mock_model]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        conns = await repo.get_connections(user_id=user_id)

        assert len(conns) == 1

    async def test_get_connections_with_event_filter(self, repo, mock_session):
        """get_connections with event_id filters by source or target."""
        user_id = uuid4()
        event_id = uuid4()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        conns = await repo.get_connections(user_id=user_id, event_id=event_id)

        assert conns == []
        mock_session.execute.assert_awaited_once()


# ======================================================================
# People
# ======================================================================


class TestPeople:
    """Tests for upsert_person and get_people."""

    async def test_upsert_person_creates_new(self, repo, mock_session):
        """When no existing person with same name, create a new one."""
        user_id = uuid4()
        person = _make_person(user_id=user_id, name="Bob Jones")

        # Simulate no existing person found
        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = scalar_mock

        mock_model = MagicMock()
        mock_model.to_domain.return_value = person

        with patch(
            "src.infrastructure.repositories.context_event_repository.PersonProfileModel"
        ) as MockModel:
            MockModel.from_domain.return_value = mock_model

            result = await repo.upsert_person(person)

        assert result.name == "Bob Jones"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    async def test_upsert_person_updates_existing(self, repo, mock_session):
        """When person with same name exists, update fields and merge aliases."""
        user_id = uuid4()
        person = _make_person(
            user_id=user_id,
            name="Alice",
            email="alice@new.com",
            role="Engineer",
            aliases=["Ali"],
            interaction_count=5,
        )

        existing_model = MagicMock()
        existing_model.phone = None
        existing_model.email = "alice@old.com"
        existing_model.role = None
        existing_model.organization = "OldCorp"
        existing_model.last_seen = None
        existing_model.interaction_count = 3
        existing_model.aliases = ["A"]
        existing_model.to_domain.return_value = person

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = existing_model
        mock_session.execute.return_value = scalar_mock

        result = await repo.upsert_person(person)

        # Email should be updated to new value
        assert existing_model.email == "alice@new.com"
        # Role should be set (was None)
        assert existing_model.role == "Engineer"
        # Organization should keep old value (person.organization is None)
        assert existing_model.organization == "OldCorp"
        # interaction_count should be the max
        assert existing_model.interaction_count == 5
        # Aliases should be merged
        assert set(existing_model.aliases) == {"A", "Ali"}
        mock_session.commit.assert_awaited_once()

    async def test_upsert_person_merge_aliases_deduplicates(self, repo, mock_session):
        """Merging aliases that overlap should not create duplicates."""
        user_id = uuid4()
        person = _make_person(user_id=user_id, name="Alice", aliases=["Al", "Ali"])

        existing_model = MagicMock()
        existing_model.phone = None
        existing_model.email = None
        existing_model.role = None
        existing_model.organization = None
        existing_model.last_seen = None
        existing_model.interaction_count = 0
        existing_model.aliases = ["Al", "Ally"]
        existing_model.to_domain.return_value = person

        scalar_mock = MagicMock()
        scalar_mock.scalar_one_or_none.return_value = existing_model
        mock_session.execute.return_value = scalar_mock

        await repo.upsert_person(person)

        merged = set(existing_model.aliases)
        assert merged == {"Al", "Ali", "Ally"}

    async def test_get_people_returns_ordered_list(self, repo, mock_session):
        """get_people returns domain objects."""
        user_id = uuid4()
        p1 = MagicMock()
        p1.to_domain.return_value = _make_person(user_id=user_id, interaction_count=10)
        p2 = MagicMock()
        p2.to_domain.return_value = _make_person(user_id=user_id, interaction_count=3)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [p1, p2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        people = await repo.get_people(user_id=user_id)

        assert len(people) == 2

    async def test_get_people_empty(self, repo, mock_session):
        """get_people returns empty list when no people exist."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        people = await repo.get_people(user_id=uuid4())

        assert people == []


# ======================================================================
# Projects
# ======================================================================


class TestProjects:
    """Tests for create_project and get_projects."""

    async def test_create_project(self, repo, mock_session):
        """create_project should add, commit, refresh, and return domain object."""
        user_id = uuid4()
        project = _make_project(user_id=user_id)

        mock_model = MagicMock()
        mock_model.to_domain.return_value = project

        with patch(
            "src.infrastructure.repositories.context_event_repository.ProjectModel"
        ) as MockModel:
            MockModel.from_domain.return_value = mock_model

            result = await repo.create_project(project)

        assert result.title == project.title
        mock_session.add.assert_called_once_with(mock_model)
        mock_session.commit.assert_awaited_once()

    async def test_get_projects_without_status_filter(self, repo, mock_session):
        """get_projects without status returns all user projects."""
        user_id = uuid4()
        mock_model = MagicMock()
        mock_model.to_domain.return_value = _make_project(user_id=user_id)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [mock_model]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        projects = await repo.get_projects(user_id=user_id)

        assert len(projects) == 1

    async def test_get_projects_with_status_filter(self, repo, mock_session):
        """get_projects with status filter should not raise."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        projects = await repo.get_projects(user_id=uuid4(), status="completed")

        assert projects == []

    async def test_get_projects_empty(self, repo, mock_session):
        """get_projects returns empty list when no projects exist."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        projects = await repo.get_projects(user_id=uuid4())

        assert projects == []
