"""Tests for reflection and review API routes."""

import math
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.reflection import create_reflection_router
from src.domain.entities.context_event import (
    ContextEvent,
    PersonProfile,
    Project,
    Commitment,
    Connection,
)
from src.domain.entities.user import User


# ---- Fixtures ----

def _make_user() -> User:
    return User(id=uuid.uuid4(), username="tester", email="t@example.com")


def _make_person(
    name: str = "Alice",
    interaction_count: int = 5,
    last_seen: datetime | None = None,
    topics: list[str] | None = None,
    dormancy_days: int = 0,
    freshness_score: float = 1.0,
    role: str | None = None,
    organization: str | None = None,
) -> PersonProfile:
    return PersonProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name=name,
        interaction_count=interaction_count,
        last_seen=last_seen or datetime.now(),
        last_activity_at=last_seen or datetime.now(),
        dormancy_days=dormancy_days,
        freshness_score=freshness_score,
        role=role,
        organization=organization,
    )


def _make_event(
    content: str = "Talked about project alpha",
    source: str = "manual_note",
    event_type: str = "note",
    topics: list[str] | None = None,
    extracted_people: list[str] | None = None,
    timestamp: datetime | None = None,
) -> ContextEvent:
    return ContextEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source=source,
        event_type=event_type,
        content=content,
        timestamp=timestamp or datetime.now(),
        topics=topics or [],
        extracted_people=extracted_people or [],
    )


def _make_commitment(
    description: str = "Send report to Alice",
    status: str = "open",
    due_date: datetime | None = None,
) -> Commitment:
    return Commitment(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        description=description,
        status=status,
        due_date=due_date,
        created_at=datetime.now(),
    )


def _make_connection(
    discovered_at: datetime | None = None,
) -> Connection:
    return Connection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source_event_id=uuid.uuid4(),
        target_event_id=uuid.uuid4(),
        connection_type="entity_match",
        strength=0.8,
        method="entity_match",
        discovered_at=discovered_at or datetime.now(),
    )


def _make_project(
    title: str = "Project Alpha",
    status: str = "active",
    dormancy_days: int = 0,
) -> Project:
    return Project(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title=title,
        status=status,
        dormancy_days=dormancy_days,
    )


@pytest.fixture
def test_user():
    return _make_user()


@pytest.fixture
def mock_deps(test_user):
    repo = AsyncMock()
    llm = AsyncMock()
    auth = MagicMock()
    auth.require_authentication = MagicMock(return_value=test_user)

    # Default empty returns
    repo.get_people = AsyncMock(return_value=[])
    repo.get_events = AsyncMock(return_value=[])
    repo.get_commitments = AsyncMock(return_value=[])
    repo.get_connections = AsyncMock(return_value=[])
    repo.get_projects = AsyncMock(return_value=[])
    repo.get_dormant_projects = AsyncMock(return_value=[])
    repo.upsert_person = AsyncMock()

    return repo, llm, auth


@pytest.fixture
def client(mock_deps):
    repo, llm, auth = mock_deps
    app = FastAPI()
    router = create_reflection_router(
        context_repo=repo,
        llm_service=llm,
        auth_middleware=auth,
    )
    app.include_router(router)

    # Override dependency injection for auth
    from fastapi import Depends

    app.dependency_overrides[auth.require_authentication] = lambda: _make_user()

    return TestClient(app)


# ================================================================
# GET /relationships
# ================================================================

class TestRelationshipStrengths:

    def test_empty_people(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_people.return_value = []

        resp = client.get("/api/v1/reflection/relationships")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_scored_people(self, client, mock_deps):
        repo, _, _ = mock_deps
        alice = _make_person(
            name="Alice",
            interaction_count=10,
            last_seen=datetime.now() - timedelta(days=1),
        )
        bob = _make_person(
            name="Bob",
            interaction_count=2,
            last_seen=datetime.now() - timedelta(days=20),
        )
        repo.get_people.return_value = [alice, bob]
        repo.get_events.return_value = [
            _make_event(content="Talked to Alice about budget", extracted_people=["Alice"], topics=["budget"]),
            _make_event(content="Meeting with Alice on strategy", extracted_people=["Alice"], topics=["strategy"]),
        ]
        repo.get_commitments.return_value = []

        resp = client.get("/api/v1/reflection/relationships")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Alice should rank higher (more recent, more interactions)
        assert data[0]["name"] == "Alice"
        assert data[0]["score"] > data[1]["score"]
        assert "recency_score" in data[0]
        assert "frequency_score" in data[0]
        assert "depth_score" in data[0]

    def test_fading_trend(self, client, mock_deps):
        repo, _, _ = mock_deps
        person = _make_person(
            name="Charlie",
            interaction_count=10,
            last_seen=datetime.now() - timedelta(days=30),
        )
        repo.get_people.return_value = [person]
        repo.get_events.return_value = []
        repo.get_commitments.return_value = []

        resp = client.get("/api/v1/reflection/relationships")
        data = resp.json()
        assert data[0]["trend"] == "fading"

    def test_strengthening_trend(self, client, mock_deps):
        repo, _, _ = mock_deps
        person = _make_person(
            name="Dana",
            interaction_count=3,
            last_seen=datetime.now(),
        )
        repo.get_people.return_value = [person]
        repo.get_events.return_value = []
        repo.get_commitments.return_value = []

        resp = client.get("/api/v1/reflection/relationships")
        data = resp.json()
        assert data[0]["trend"] == "strengthening"

    def test_open_commitments_counted(self, client, mock_deps):
        repo, _, _ = mock_deps
        person = _make_person(name="Eve")
        repo.get_people.return_value = [person]
        repo.get_events.return_value = []
        repo.get_commitments.return_value = [
            _make_commitment(description="Send report to Eve", status="open"),
            _make_commitment(description="Call Eve tomorrow", status="open"),
        ]

        resp = client.get("/api/v1/reflection/relationships")
        data = resp.json()
        assert data[0]["open_commitments"] == 2


# ================================================================
# GET /people/{person_id}/dossier
# ================================================================

class TestPersonDossier:

    def test_not_found(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_people.return_value = []

        resp = client.get(f"/api/v1/reflection/people/{uuid.uuid4()}/dossier")
        assert resp.status_code == 404

    def test_returns_dossier(self, client, mock_deps):
        repo, llm, _ = mock_deps
        alice = _make_person(name="Alice", role="Engineer", organization="Acme")
        repo.get_people.return_value = [alice]
        repo.get_events.return_value = [
            _make_event(
                content="Met with Alice about Q2 roadmap",
                extracted_people=["Alice"],
                topics=["roadmap", "Q2"],
                timestamp=datetime.now() - timedelta(days=2),
            ),
        ]
        repo.get_commitments.return_value = [
            _make_commitment(description="Send Alice the budget doc", status="open"),
        ]
        llm.generate.return_value = '{"talking_points": ["Discuss Q2 roadmap progress", "Follow up on budget doc"]}'

        resp = client.get(f"/api/v1/reflection/people/{alice.id}/dossier")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["role"] == "Engineer"
        assert data["organization"] == "Acme"
        assert data["relationship_strength"] > 0
        assert len(data["shared_topics"]) > 0
        assert len(data["open_commitments"]) == 1
        assert len(data["suggested_talking_points"]) == 2
        assert len(data["interaction_timeline"]) > 0

    def test_dossier_llm_failure_graceful(self, client, mock_deps):
        repo, llm, _ = mock_deps
        alice = _make_person(name="Alice")
        repo.get_people.return_value = [alice]
        repo.get_events.return_value = [
            _make_event(content="Called Alice", extracted_people=["Alice"]),
        ]
        repo.get_commitments.return_value = []
        llm.generate.side_effect = Exception("LLM down")

        resp = client.get(f"/api/v1/reflection/people/{alice.id}/dossier")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suggested_talking_points"] == []

    def test_dossier_no_events(self, client, mock_deps):
        repo, llm, _ = mock_deps
        alice = _make_person(name="Alice")
        repo.get_people.return_value = [alice]
        repo.get_events.return_value = []
        repo.get_commitments.return_value = []

        resp = client.get(f"/api/v1/reflection/people/{alice.id}/dossier")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recent_events"] == []
        assert data["shared_topics"] == []
        assert data["suggested_talking_points"] == []


# ================================================================
# GET /review/weekly
# ================================================================

class TestWeeklyReview:

    def test_empty_week(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = []
        repo.get_people.return_value = []
        repo.get_connections.return_value = []
        repo.get_commitments.return_value = []
        repo.get_projects.return_value = []
        repo.get_dormant_projects.return_value = []

        resp = client.get("/api/v1/reflection/review/weekly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events_captured"] == 0
        assert data["new_connections"] == 0

    def test_weekly_review_with_data(self, client, mock_deps):
        repo, llm, _ = mock_deps
        now = datetime.now()
        repo.get_events.return_value = [
            _make_event(content="Planning session", topics=["planning"], timestamp=now - timedelta(days=1)),
            _make_event(content="Code review", topics=["engineering"], timestamp=now - timedelta(days=2)),
        ]
        repo.get_people.return_value = [
            _make_person(name="Alice", last_seen=now - timedelta(days=1)),
            _make_person(name="Bob", last_seen=now - timedelta(days=30), dormancy_days=30),
        ]
        repo.get_connections.return_value = [
            _make_connection(discovered_at=now - timedelta(days=1)),
        ]
        repo.get_commitments.return_value = [
            _make_commitment(description="Task A", status="fulfilled"),
        ]
        repo.get_projects.return_value = [_make_project()]
        repo.get_dormant_projects.return_value = []

        llm.generate.return_value = '{"summary": "Great week", "reflection_prompts": ["What went well?"]}'

        resp = client.get("/api/v1/reflection/review/weekly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["events_captured"] == 2
        assert data["new_connections"] == 1
        assert len(data["top_topics"]) > 0
        assert data["ai_summary"] == "Great week"

    def test_weekly_review_llm_failure(self, client, mock_deps):
        repo, llm, _ = mock_deps
        repo.get_events.return_value = [_make_event()]
        repo.get_people.return_value = []
        repo.get_connections.return_value = []
        repo.get_commitments.return_value = []
        repo.get_projects.return_value = []
        repo.get_dormant_projects.return_value = []
        llm.generate.side_effect = Exception("LLM down")

        resp = client.get("/api/v1/reflection/review/weekly")
        assert resp.status_code == 200
        data = resp.json()
        assert "1 events" in data["ai_summary"]


# ================================================================
# GET /review/monthly
# ================================================================

class TestMonthlyReflection:

    def test_empty_month(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = []
        repo.get_people.return_value = []
        repo.get_commitments.return_value = []

        resp = client.get("/api/v1/reflection/review/monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 0

    def test_monthly_with_data(self, client, mock_deps):
        repo, llm, _ = mock_deps
        now = datetime.now()
        repo.get_events.return_value = [
            _make_event(content="Big idea", topics=["innovation"], timestamp=now - timedelta(days=5)),
        ]
        repo.get_people.return_value = [
            _make_person(name="Alice", dormancy_days=25, freshness_score=0.3),
            _make_person(name="Bob", interaction_count=15, freshness_score=0.9),
        ]
        repo.get_commitments.return_value = [
            _make_commitment(description="Ship feature X", status="fulfilled"),
        ]

        llm.generate.return_value = '{"reflection": "A month of growth", "patterns": ["Focus on innovation"], "idea_evolution": ["Feature X evolved from concept to shipped"]}'

        resp = client.get("/api/v1/reflection/review/monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 1
        assert data["ai_reflection"] == "A month of growth"
        assert len(data["patterns"]) == 1
        assert len(data["relationship_changes"]) > 0

    def test_monthly_llm_failure(self, client, mock_deps):
        repo, llm, _ = mock_deps
        repo.get_events.return_value = [_make_event()]
        repo.get_people.return_value = []
        repo.get_commitments.return_value = []
        llm.generate.side_effect = Exception("LLM down")

        resp = client.get("/api/v1/reflection/review/monthly")
        assert resp.status_code == 200
        data = resp.json()
        assert "1 events" in data["ai_reflection"]


# ================================================================
# POST /people/merge
# ================================================================

class TestPeopleMerge:

    def test_merge_not_found(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_people.return_value = []

        resp = client.post(
            "/api/v1/reflection/people/merge",
            params={"source_id": str(uuid.uuid4()), "target_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_merge_success(self, client, mock_deps):
        repo, _, _ = mock_deps
        source = _make_person(name="Mom", interaction_count=5, role="Family")
        target = _make_person(name="Jane Doe", interaction_count=3, organization="Home")
        repo.get_people.return_value = [source, target]

        resp = client.post(
            "/api/v1/reflection/people/merge",
            params={"source_id": str(source.id), "target_id": str(target.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["merged_into"] == str(target.id)
        assert data["absorbed"] == str(source.id)
        assert "Mom" in data["new_aliases"]
        assert data["combined_interactions"] == 8

        # Verify upsert was called
        repo.upsert_person.assert_called_once()
        merged = repo.upsert_person.call_args[0][0]
        assert merged.name == "Jane Doe"
        assert merged.role == "Family"  # source fills in missing target fields
        assert merged.organization == "Home"

    def test_merge_source_missing(self, client, mock_deps):
        repo, _, _ = mock_deps
        target = _make_person(name="Jane")
        repo.get_people.return_value = [target]

        resp = client.post(
            "/api/v1/reflection/people/merge",
            params={"source_id": str(uuid.uuid4()), "target_id": str(target.id)},
        )
        assert resp.status_code == 404
