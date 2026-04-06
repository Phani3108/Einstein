"""Unit tests for context API routes with mocked dependencies."""

import uuid
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from src.api.routes.context import create_context_router
from src.domain.entities.context_event import (
    Connection,
    ContextEvent,
    PersonProfile,
    Project,
)
from src.domain.entities.user import User


# ---- Helpers ----


def _make_user():
    return User(
        id=uuid4(),
        email="ctx@example.com",
        hashed_password="hashed",
    )


def _make_event(user_id, **kw):
    return ContextEvent(
        id=kw.get("id", uuid4()),
        user_id=user_id,
        source=kw.get("source", "notification"),
        source_id=kw.get("source_id", "src-1"),
        event_type=kw.get("event_type", "message"),
        content=kw.get("content", "test content"),
        structured_data=kw.get("structured_data", {}),
        timestamp=kw.get("timestamp", datetime(2025, 1, 15, 10, 0, 0)),
        extracted_people=kw.get("extracted_people", []),
        topics=kw.get("topics", []),
        tier0_at=kw.get("tier0_at", None),
        tier1_at=kw.get("tier1_at", None),
        tier2_at=kw.get("tier2_at", None),
        created_at=kw.get("created_at", datetime(2025, 1, 15, 10, 0, 0)),
    )


def _make_connection(user_id, **kw):
    return Connection(
        id=kw.get("id", uuid4()),
        user_id=user_id,
        source_event_id=kw.get("source_event_id", uuid4()),
        target_event_id=kw.get("target_event_id", uuid4()),
        connection_type=kw.get("connection_type", "same_topic"),
        strength=kw.get("strength", 0.85),
        evidence=kw.get("evidence", "shared entity"),
        method=kw.get("method", "entity_match"),
        discovered_at=kw.get("discovered_at", datetime(2025, 1, 15, 10, 0, 0)),
    )


def _make_person(user_id, **kw):
    return PersonProfile(
        id=kw.get("id", uuid4()),
        user_id=user_id,
        name=kw.get("name", "Alice"),
        aliases=kw.get("aliases", []),
        phone=kw.get("phone", None),
        email=kw.get("email", None),
        role=kw.get("role", None),
        organization=kw.get("organization", None),
        last_seen=kw.get("last_seen", None),
        interaction_count=kw.get("interaction_count", 0),
        created_at=kw.get("created_at", datetime(2025, 1, 15, 10, 0, 0)),
    )


def _make_project(user_id, **kw):
    return Project(
        id=kw.get("id", uuid4()),
        user_id=user_id,
        title=kw.get("title", "Project Alpha"),
        description=kw.get("description", "desc"),
        status=kw.get("status", "active"),
        deadline=kw.get("deadline", None),
        created_at=kw.get("created_at", datetime(2025, 1, 15, 10, 0, 0)),
        updated_at=kw.get("updated_at", datetime(2025, 1, 15, 10, 0, 0)),
    )


# ---- Fixtures ----


@pytest.fixture
def test_user():
    return _make_user()


@pytest.fixture
def mock_context_repo():
    repo = AsyncMock()
    repo.ingest_batch = AsyncMock(return_value=0)
    repo.get_events = AsyncMock(return_value=[])
    repo.get_connections = AsyncMock(return_value=[])
    repo.upsert_person = AsyncMock()
    repo.get_people = AsyncMock(return_value=[])
    repo.create_project = AsyncMock()
    repo.get_projects = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_auth_middleware(test_user):
    auth = Mock()
    auth.require_authentication = AsyncMock(return_value=test_user)
    return auth


@pytest.fixture
def client(mock_context_repo, mock_auth_middleware):
    app = FastAPI()
    router = create_context_router(mock_context_repo, mock_auth_middleware)
    app.include_router(router)
    return TestClient(app)


# ======================================================================
# POST /api/v1/context/ingest
# ======================================================================


class TestIngestEndpoint:
    """Tests for POST /api/v1/context/ingest."""

    async def test_ingest_events_success(self, client, mock_context_repo):
        """Successful ingestion returns inserted count and total."""
        mock_context_repo.ingest_batch.return_value = 2

        payload = {
            "events": [
                {
                    "source": "notification",
                    "source_id": "n1",
                    "event_type": "message",
                    "content": "Hello",
                    "timestamp": "2025-01-15T10:00:00",
                },
                {
                    "source": "calendar",
                    "source_id": "c1",
                    "event_type": "meeting",
                    "content": "Team standup",
                    "timestamp": "2025-01-15T11:00:00",
                },
            ]
        }

        response = client.post(
            "/api/v1/context/ingest",
            json=payload,
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["inserted"] == 2
        assert data["total"] == 2
        mock_context_repo.ingest_batch.assert_awaited_once()

    async def test_ingest_empty_batch(self, client, mock_context_repo):
        """Empty event list should succeed with 0/0."""
        mock_context_repo.ingest_batch.return_value = 0

        response = client.post(
            "/api/v1/context/ingest",
            json={"events": []},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == {"inserted": 0, "total": 0}

    async def test_ingest_missing_required_fields(self, client):
        """Missing required fields in event should return 422."""
        response = client.post(
            "/api/v1/context/ingest",
            json={"events": [{"source": "notification"}]},  # missing event_type, timestamp
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 422


# ======================================================================
# GET /api/v1/context/events
# ======================================================================


class TestGetEventsEndpoint:
    """Tests for GET /api/v1/context/events."""

    async def test_get_events_success(self, client, mock_context_repo, test_user):
        """Returns events as JSON list."""
        event = _make_event(test_user.id)
        mock_context_repo.get_events.return_value = [event]

        response = client.get(
            "/api/v1/context/events",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "notification"
        assert data[0]["id"] == str(event.id)

    async def test_get_events_with_filters(self, client, mock_context_repo, test_user):
        """Query params are forwarded to the repository."""
        mock_context_repo.get_events.return_value = []

        response = client.get(
            "/api/v1/context/events?source=email&limit=10&offset=5",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        call_kwargs = mock_context_repo.get_events.call_args[1]
        assert call_kwargs["source"] == "email"
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    async def test_get_events_empty(self, client, mock_context_repo):
        """No events returns empty list."""
        mock_context_repo.get_events.return_value = []

        response = client.get(
            "/api/v1/context/events",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []


# ======================================================================
# GET /api/v1/context/connections
# ======================================================================


class TestGetConnectionsEndpoint:
    """Tests for GET /api/v1/context/connections."""

    async def test_get_connections_success(self, client, mock_context_repo, test_user):
        """Returns connections list."""
        conn = _make_connection(test_user.id)
        mock_context_repo.get_connections.return_value = [conn]

        response = client.get(
            "/api/v1/context/connections",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["connection_type"] == "same_topic"
        assert data[0]["strength"] == 0.85

    async def test_get_connections_with_event_id(self, client, mock_context_repo, test_user):
        """Passing event_id filters connections."""
        mock_context_repo.get_connections.return_value = []
        event_id = str(uuid4())

        response = client.get(
            f"/api/v1/context/connections?event_id={event_id}",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        call_kwargs = mock_context_repo.get_connections.call_args[1]
        assert call_kwargs["event_id"] == uuid.UUID(event_id)

    async def test_get_connections_empty(self, client, mock_context_repo):
        """No connections returns empty list."""
        mock_context_repo.get_connections.return_value = []

        response = client.get(
            "/api/v1/context/connections",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []


# ======================================================================
# GET /api/v1/context/timeline
# ======================================================================


class TestTimelineEndpoint:
    """Tests for GET /api/v1/context/timeline."""

    async def test_timeline_returns_events(self, client, mock_context_repo, test_user):
        """Timeline endpoint returns events across all sources."""
        event = _make_event(test_user.id, source="calendar")
        mock_context_repo.get_events.return_value = [event]

        response = client.get(
            "/api/v1/context/timeline",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "calendar"

    async def test_timeline_with_limit(self, client, mock_context_repo, test_user):
        """Timeline accepts limit parameter."""
        mock_context_repo.get_events.return_value = []

        response = client.get(
            "/api/v1/context/timeline?limit=10",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        call_kwargs = mock_context_repo.get_events.call_args[1]
        assert call_kwargs["limit"] == 10


# ======================================================================
# POST /api/v1/context/people
# ======================================================================


class TestUpsertPersonEndpoint:
    """Tests for POST /api/v1/context/people."""

    async def test_upsert_person_success(self, client, mock_context_repo, test_user):
        """Create a new person returns the person object."""
        person = _make_person(test_user.id, name="Bob", email="bob@example.com")
        mock_context_repo.upsert_person.return_value = person

        response = client.post(
            "/api/v1/context/people",
            json={"name": "Bob", "email": "bob@example.com"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Bob"
        assert data["email"] == "bob@example.com"
        mock_context_repo.upsert_person.assert_awaited_once()

    async def test_upsert_person_with_aliases(self, client, mock_context_repo, test_user):
        """Person with aliases is correctly passed through."""
        person = _make_person(
            test_user.id, name="Robert", aliases=["Bob", "Rob"]
        )
        mock_context_repo.upsert_person.return_value = person

        response = client.post(
            "/api/v1/context/people",
            json={"name": "Robert", "aliases": ["Bob", "Rob"]},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json()["aliases"] == ["Bob", "Rob"]

    async def test_upsert_person_missing_name(self, client):
        """Missing required name field returns 422."""
        response = client.post(
            "/api/v1/context/people",
            json={"email": "noname@example.com"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 422


# ======================================================================
# GET /api/v1/context/people
# ======================================================================


class TestGetPeopleEndpoint:
    """Tests for GET /api/v1/context/people."""

    async def test_get_people_success(self, client, mock_context_repo, test_user):
        """Returns list of people."""
        person = _make_person(test_user.id, name="Carol")
        mock_context_repo.get_people.return_value = [person]

        response = client.get(
            "/api/v1/context/people",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Carol"

    async def test_get_people_empty(self, client, mock_context_repo):
        """No people returns empty list."""
        mock_context_repo.get_people.return_value = []

        response = client.get(
            "/api/v1/context/people",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []


# ======================================================================
# POST /api/v1/context/projects
# ======================================================================


class TestCreateProjectEndpoint:
    """Tests for POST /api/v1/context/projects."""

    async def test_create_project_success(self, client, mock_context_repo, test_user):
        """Successful project creation returns project object."""
        project = _make_project(test_user.id, title="Launch v2")
        mock_context_repo.create_project.return_value = project

        response = client.post(
            "/api/v1/context/projects",
            json={"title": "Launch v2", "description": "Ship it"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Launch v2"
        assert data["status"] == "active"
        mock_context_repo.create_project.assert_awaited_once()

    async def test_create_project_with_deadline(self, client, mock_context_repo, test_user):
        """Project with deadline is accepted."""
        project = _make_project(
            test_user.id,
            title="Q2 Goals",
            deadline=datetime(2025, 6, 30),
        )
        mock_context_repo.create_project.return_value = project

        response = client.post(
            "/api/v1/context/projects",
            json={
                "title": "Q2 Goals",
                "description": "goals",
                "deadline": "2025-06-30T00:00:00",
            },
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json()["deadline"] is not None

    async def test_create_project_missing_title(self, client):
        """Missing required title returns 422."""
        response = client.post(
            "/api/v1/context/projects",
            json={"description": "no title"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 422


# ======================================================================
# GET /api/v1/context/projects
# ======================================================================


class TestGetProjectsEndpoint:
    """Tests for GET /api/v1/context/projects."""

    async def test_get_projects_success(self, client, mock_context_repo, test_user):
        """Returns project list."""
        project = _make_project(test_user.id)
        mock_context_repo.get_projects.return_value = [project]

        response = client.get(
            "/api/v1/context/projects",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    async def test_get_projects_with_status_filter(self, client, mock_context_repo, test_user):
        """Status query param is passed to repo."""
        mock_context_repo.get_projects.return_value = []

        response = client.get(
            "/api/v1/context/projects?status=completed",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        call_kwargs = mock_context_repo.get_projects.call_args
        assert call_kwargs[1]["status"] == "completed"

    async def test_get_projects_empty(self, client, mock_context_repo):
        """No projects returns empty list."""
        mock_context_repo.get_projects.return_value = []

        response = client.get(
            "/api/v1/context/projects",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []


# ======================================================================
# GET /api/v1/context/sync/pull
# ======================================================================


class TestSyncPullEndpoint:
    """Tests for GET /api/v1/context/sync/pull."""

    async def test_sync_pull_returns_events_and_connections(
        self, client, mock_context_repo, test_user
    ):
        """Sync pull returns events, connections, and server_time."""
        event = _make_event(test_user.id)
        conn = _make_connection(test_user.id)
        mock_context_repo.get_events.return_value = [event]
        mock_context_repo.get_connections.return_value = [conn]

        response = client.get(
            "/api/v1/context/sync/pull",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert len(data["connections"]) == 1
        assert "server_time" in data

    async def test_sync_pull_with_since_param(self, client, mock_context_repo, test_user):
        """Sync pull with since parameter filters events."""
        mock_context_repo.get_events.return_value = []
        mock_context_repo.get_connections.return_value = []

        response = client.get(
            "/api/v1/context/sync/pull?since=2025-01-01T00:00:00",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        call_kwargs = mock_context_repo.get_events.call_args[1]
        assert call_kwargs["since"] is not None

    async def test_sync_pull_empty(self, client, mock_context_repo):
        """Sync pull with no data returns empty lists."""
        mock_context_repo.get_events.return_value = []
        mock_context_repo.get_connections.return_value = []

        response = client.get(
            "/api/v1/context/sync/pull",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["connections"] == []
