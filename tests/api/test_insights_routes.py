"""Unit tests for insights API routes with mocked dependencies."""

import json
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from src.api.routes.insights import create_insights_router
from src.domain.entities.context_event import ContextEvent, PersonProfile
from src.domain.entities.user import User


# ---- Helpers ----


def _make_user():
    return User(
        id=uuid4(),
        email="insight@example.com",
        hashed_password="hashed",
    )


def _make_event(user_id, **kw):
    return ContextEvent(
        id=kw.get("id", uuid4()),
        user_id=user_id,
        source=kw.get("source", "notification"),
        source_id=kw.get("source_id", None),
        event_type=kw.get("event_type", "message"),
        content=kw.get("content", "some content"),
        structured_data=kw.get("structured_data", {}),
        timestamp=kw.get("timestamp", datetime.now()),
        extracted_people=kw.get("extracted_people", []),
        topics=kw.get("topics", []),
        tier0_at=kw.get("tier0_at", None),
        tier1_at=kw.get("tier1_at", None),
        tier2_at=kw.get("tier2_at", None),
        created_at=kw.get("created_at", datetime.now()),
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
        created_at=kw.get("created_at", datetime.now()),
    )


# ---- Fixtures ----


@pytest.fixture
def test_user():
    return _make_user()


@pytest.fixture
def mock_context_repo():
    repo = AsyncMock()
    repo.get_events = AsyncMock(return_value=[])
    repo.get_people = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_llm_service():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="{}")
    return llm


@pytest.fixture
def mock_auth_middleware(test_user):
    auth = Mock()
    auth.require_authentication = AsyncMock(return_value=test_user)
    return auth


@pytest.fixture
def client(mock_context_repo, mock_llm_service, mock_auth_middleware):
    app = FastAPI()
    router = create_insights_router(mock_context_repo, mock_llm_service, mock_auth_middleware)
    app.include_router(router)
    return TestClient(app)


# ======================================================================
# POST /api/v1/insights/briefing
# ======================================================================


class TestBriefingEndpoint:
    """Tests for POST /api/v1/insights/briefing."""

    async def test_briefing_daily_success(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """LLM returns valid JSON — briefing is built from it."""
        event = _make_event(test_user.id, content="Team standup went well")
        mock_context_repo.get_events.return_value = [event]

        llm_response = json.dumps({
            "summary": "Productive day with team standup.",
            "highlights": ["Standup completed"],
            "attention_needed": ["Review PR #42"],
            "themes": ["teamwork"],
        })
        mock_llm_service.generate.return_value = llm_response

        response = client.post(
            "/api/v1/insights/briefing",
            json={"period": "daily"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Productive day with team standup."
        assert "Standup completed" in data["highlights"]
        assert "teamwork" in data["themes"]
        mock_llm_service.generate.assert_awaited_once()

    async def test_briefing_weekly_success(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """Weekly briefing uses 7-day window."""
        events = [_make_event(test_user.id) for _ in range(3)]
        mock_context_repo.get_events.return_value = events

        llm_response = json.dumps({
            "summary": "Busy week.",
            "highlights": [],
            "attention_needed": [],
            "themes": ["productivity"],
        })
        mock_llm_service.generate.return_value = llm_response

        response = client.post(
            "/api/v1/insights/briefing",
            json={"period": "weekly"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json()["summary"] == "Busy week."

    async def test_briefing_no_events_returns_empty_summary(
        self, client, mock_context_repo, mock_llm_service
    ):
        """When no events exist, return a default summary without calling LLM."""
        mock_context_repo.get_events.return_value = []

        response = client.post(
            "/api/v1/insights/briefing",
            json={"period": "daily"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "No recent activity" in data["summary"]
        mock_llm_service.generate.assert_not_awaited()

    async def test_briefing_llm_failure_returns_fallback(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """When LLM raises an exception, return graceful fallback."""
        events = [_make_event(test_user.id, source="email")]
        mock_context_repo.get_events.return_value = events
        mock_llm_service.generate.side_effect = Exception("LLM unavailable")

        response = client.post(
            "/api/v1/insights/briefing",
            json={"period": "daily"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        # Fallback summary mentions event count and source count
        assert "1 events" in data["summary"] or "1" in data["summary"]

    async def test_briefing_llm_returns_invalid_json_fallback(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """When LLM returns non-JSON text, fallback is used."""
        mock_context_repo.get_events.return_value = [_make_event(test_user.id)]
        mock_llm_service.generate.return_value = "This is not JSON at all."

        response = client.post(
            "/api/v1/insights/briefing",
            json={"period": "daily"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        # Should get fallback, not crash
        data = response.json()
        assert data["summary"] != ""


# ======================================================================
# POST /api/v1/insights/prep
# ======================================================================


class TestPrepEndpoint:
    """Tests for POST /api/v1/insights/prep."""

    async def test_prep_success(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """LLM returns valid JSON prep pack."""
        mock_context_repo.get_events.return_value = [_make_event(test_user.id)]
        mock_context_repo.get_people.return_value = [
            _make_person(test_user.id, name="Bob", role="PM")
        ]

        llm_response = json.dumps({
            "summary": "Ready for the day.",
            "key_points": ["Review design doc"],
            "open_questions": ["Budget approval?"],
            "relevant_history": ["Last meeting discussed timelines"],
            "suggested_actions": ["Prepare slides"],
        })
        mock_llm_service.generate.return_value = llm_response

        response = client.post(
            "/api/v1/insights/prep",
            json={"focus_type": "day", "context": {"meeting": "standup"}},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Ready for the day."
        assert "Review design doc" in data["key_points"]

    async def test_prep_llm_failure_returns_fallback(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """When LLM fails, return a fallback prep response."""
        mock_context_repo.get_events.return_value = [_make_event(test_user.id)]
        mock_context_repo.get_people.return_value = []
        mock_llm_service.generate.side_effect = RuntimeError("timeout")

        response = client.post(
            "/api/v1/insights/prep",
            json={"focus_type": "meeting"},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Could not generate prep" in data["summary"]

    async def test_prep_default_focus_type(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """Default focus_type is 'day'."""
        mock_context_repo.get_events.return_value = []
        mock_context_repo.get_people.return_value = []
        mock_llm_service.generate.return_value = json.dumps({
            "summary": "No data",
            "key_points": [],
            "open_questions": [],
            "relevant_history": [],
            "suggested_actions": [],
        })

        response = client.post(
            "/api/v1/insights/prep",
            json={},
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200


# ======================================================================
# GET /api/v1/insights/suggestions
# ======================================================================


class TestSuggestionsEndpoint:
    """Tests for GET /api/v1/insights/suggestions."""

    async def test_suggestions_success(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """LLM returns a list of suggestions."""
        mock_context_repo.get_events.return_value = [_make_event(test_user.id)]
        mock_context_repo.get_people.return_value = [
            _make_person(test_user.id, last_seen=datetime.now() - timedelta(days=30))
        ]

        llm_response = json.dumps({
            "suggestions": [
                {
                    "type": "follow_up",
                    "title": "Reconnect with Alice",
                    "description": "Haven't spoken in 30 days",
                    "confidence": 0.9,
                },
            ]
        })
        mock_llm_service.generate.return_value = llm_response

        response = client.get(
            "/api/v1/insights/suggestions",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["type"] == "follow_up"
        assert data[0]["confidence"] == 0.9

    async def test_suggestions_llm_failure_returns_empty_list(
        self, client, mock_context_repo, mock_llm_service, test_user
    ):
        """When LLM fails, return an empty list instead of crashing."""
        mock_context_repo.get_events.return_value = [_make_event(test_user.id)]
        mock_context_repo.get_people.return_value = []
        mock_llm_service.generate.side_effect = Exception("API error")

        response = client.get(
            "/api/v1/insights/suggestions",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_suggestions_no_events(
        self, client, mock_context_repo, mock_llm_service
    ):
        """With no events, LLM is still called but may return empty suggestions."""
        mock_context_repo.get_events.return_value = []
        mock_context_repo.get_people.return_value = []
        mock_llm_service.generate.return_value = json.dumps({"suggestions": []})

        response = client.get(
            "/api/v1/insights/suggestions",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []


# ======================================================================
# GET /api/v1/insights/people/{person_id}
# ======================================================================


class TestPersonInsightsEndpoint:
    """Tests for GET /api/v1/insights/people/{person_id}."""

    async def test_person_insights_success(
        self, client, mock_context_repo, test_user
    ):
        """Returns insights for an existing person."""
        person_id = uuid4()
        person = _make_person(
            test_user.id,
            id=person_id,
            name="Dave",
            interaction_count=7,
            last_seen=datetime.now() - timedelta(days=3),
        )
        mock_context_repo.get_people.return_value = [person]

        # Events mentioning Dave
        event_with_dave = _make_event(
            test_user.id,
            content="Had lunch with Dave",
            extracted_people=["Dave"],
            topics=["lunch", "networking"],
        )
        event_without_dave = _make_event(
            test_user.id,
            content="Code review session",
            extracted_people=[],
            topics=["engineering"],
        )
        mock_context_repo.get_events.return_value = [event_with_dave, event_without_dave]

        response = client.get(
            f"/api/v1/insights/people/{person_id}",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Dave"
        assert data["interaction_count"] == 7
        assert data["recent_events"] == 1  # only the event mentioning Dave
        assert data["follow_up_needed"] is False  # seen 3 days ago

    async def test_person_insights_follow_up_needed(
        self, client, mock_context_repo, test_user
    ):
        """Person not seen in >14 days triggers follow_up_needed."""
        person_id = uuid4()
        person = _make_person(
            test_user.id,
            id=person_id,
            name="Eve",
            last_seen=datetime.now() - timedelta(days=20),
        )
        mock_context_repo.get_people.return_value = [person]
        mock_context_repo.get_events.return_value = []

        response = client.get(
            f"/api/v1/insights/people/{person_id}",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json()["follow_up_needed"] is True

    async def test_person_insights_not_found(
        self, client, mock_context_repo
    ):
        """Non-existent person_id returns 404."""
        mock_context_repo.get_people.return_value = []

        response = client.get(
            f"/api/v1/insights/people/{uuid4()}",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 404
        assert "Person not found" in response.json()["detail"]

    async def test_person_insights_extracts_topics(
        self, client, mock_context_repo, test_user
    ):
        """Topics are collected from events mentioning the person."""
        person_id = uuid4()
        person = _make_person(test_user.id, id=person_id, name="Frank")
        mock_context_repo.get_people.return_value = [person]

        events = [
            _make_event(
                test_user.id,
                extracted_people=["Frank"],
                topics=["design", "ux"],
            ),
            _make_event(
                test_user.id,
                extracted_people=["Frank"],
                topics=["design", "frontend"],
            ),
        ]
        mock_context_repo.get_events.return_value = events

        response = client.get(
            f"/api/v1/insights/people/{person_id}",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        # Topics should be de-duplicated
        assert "design" in data["top_topics"]
        assert data["recent_events"] == 2


# ======================================================================
# GET /api/v1/insights/patterns
# ======================================================================


class TestPatternsEndpoint:
    """Tests for GET /api/v1/insights/patterns."""

    async def test_patterns_success(self, client, mock_context_repo, test_user):
        """Patterns are derived from event topics."""
        events = [
            _make_event(test_user.id, topics=["engineering", "python"]),
            _make_event(test_user.id, topics=["engineering", "testing"]),
            _make_event(test_user.id, topics=["python"]),
        ]
        mock_context_repo.get_events.return_value = events

        response = client.get(
            "/api/v1/insights/patterns",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        # engineering appears 2x, python 2x, testing 1x
        themes = {p["theme"]: p["event_count"] for p in data}
        assert themes["engineering"] == 2
        assert themes["python"] == 2
        assert themes["testing"] == 1

    async def test_patterns_empty_when_no_topics(self, client, mock_context_repo, test_user):
        """Events without topics produce no patterns."""
        events = [_make_event(test_user.id, topics=[])]
        mock_context_repo.get_events.return_value = events

        response = client.get(
            "/api/v1/insights/patterns",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_patterns_no_events(self, client, mock_context_repo):
        """No events returns empty patterns list."""
        mock_context_repo.get_events.return_value = []

        response = client.get(
            "/api/v1/insights/patterns",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_patterns_with_days_param(self, client, mock_context_repo, test_user):
        """days query parameter is accepted."""
        mock_context_repo.get_events.return_value = []

        response = client.get(
            "/api/v1/insights/patterns?days=7",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_patterns_limited_to_top_10(self, client, mock_context_repo, test_user):
        """At most 10 patterns are returned, sorted by event_count desc."""
        topics = [f"topic-{i}" for i in range(15)]
        events = [_make_event(test_user.id, topics=topics)]
        mock_context_repo.get_events.return_value = events

        response = client.get(
            "/api/v1/insights/patterns",
            headers={"Authorization": "Bearer token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
