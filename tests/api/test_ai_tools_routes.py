"""Tests for the 5 contextual AI tools API routes."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.ai_tools import create_ai_tools_router
from src.domain.entities.context_event import ContextEvent, PersonProfile, Project
from src.domain.entities.user import User


def _make_user():
    return User(id=uuid.uuid4(), username="tester", email="t@example.com")


def _make_event(content="Discussed roadmap with Alice", source="manual_note", topics=None, extracted_people=None):
    return ContextEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source=source,
        event_type="note",
        content=content,
        timestamp=datetime.now(),
        topics=topics or [],
        extracted_people=extracted_people or [],
    )


def _make_person(name="Alice"):
    return PersonProfile(
        id=uuid.uuid4(), user_id=uuid.uuid4(), name=name, interaction_count=5,
        last_seen=datetime.now(),
    )


@pytest.fixture
def mock_deps():
    repo = AsyncMock()
    llm = AsyncMock()
    auth = MagicMock()
    auth.require_authentication = MagicMock(return_value=_make_user())
    repo.get_events = AsyncMock(return_value=[])
    repo.get_people = AsyncMock(return_value=[])
    repo.get_projects = AsyncMock(return_value=[])
    repo.get_commitments = AsyncMock(return_value=[])
    return repo, llm, auth


@pytest.fixture
def client(mock_deps):
    repo, llm, auth = mock_deps
    app = FastAPI()
    router = create_ai_tools_router(
        context_repo=repo, llm_service=llm, auth_middleware=auth
    )
    app.include_router(router)
    app.dependency_overrides[auth.require_authentication] = _make_user
    return TestClient(app)


# ================================================================
# POST /tools/summarize
# ================================================================

class TestSummarize:

    def test_summarize_text(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.return_value = '{"summary": "Brief summary", "key_points": ["Point A", "Point B"]}'

        resp = client.post(
            "/api/v1/tools/summarize",
            json={"content": "A long document about many topics " * 20},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "Brief summary"
        assert len(data["key_points"]) == 2

    def test_summarize_llm_failure(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.side_effect = Exception("LLM down")

        resp = client.post(
            "/api/v1/tools/summarize",
            json={"content": "Some content to summarize"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] != ""


# ================================================================
# POST /tools/connect
# ================================================================

class TestConnect:

    def test_connect_finds_related(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = [
            _make_event("Discussed roadmap with Alice", topics=["roadmap"], extracted_people=["Alice"]),
            _make_event("Q3 roadmap planning", topics=["roadmap"]),
            _make_event("Totally unrelated cooking recipe"),
        ]

        resp = client.post(
            "/api/v1/tools/connect",
            json={"content": "roadmap", "limit": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["connections"]) >= 1

    def test_connect_empty(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = []

        resp = client.post(
            "/api/v1/tools/connect",
            json={"content": "nonexistent topic"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["connections"] == []


# ================================================================
# POST /tools/prepare
# ================================================================

class TestPrepare:

    def test_prepare_for_person(self, client, mock_deps):
        repo, llm, _ = mock_deps
        alice = _make_person("Alice")
        repo.get_people.return_value = [alice]
        repo.get_events.return_value = [
            _make_event("Met with Alice about budget", extracted_people=["Alice"]),
        ]
        repo.get_commitments.return_value = []
        llm.generate.return_value = '{"summary": "Prep for Alice", "key_points": ["Budget review"], "open_questions": [], "relevant_history": [], "suggested_actions": []}'

        resp = client.post(
            "/api/v1/tools/prepare",
            json={"focus_type": "person", "focus_id": str(alice.id), "context": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_prepare_llm_failure(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.side_effect = Exception("LLM down")

        resp = client.post(
            "/api/v1/tools/prepare",
            json={"focus_type": "day", "context": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data


# ================================================================
# POST /tools/extract
# ================================================================

class TestExtract:

    def test_extract_structured(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.return_value = '{"action_items": [{"task": "Send report", "assignee": "Alice", "deadline": "2024-03-15", "priority": "high"}], "decisions": [{"title": "Go with vendor A", "description": "Cost effective", "reasoning": "Lower TCO"}], "commitments": [{"description": "Follow up with Bob", "due_date": "2024-03-20", "person": "Bob"}]}'

        resp = client.post(
            "/api/v1/tools/extract",
            json={"content": "Send the report to Alice by March 15. We decided to go with vendor A because of lower TCO. I'll follow up with Bob by March 20."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["action_items"]) == 1
        assert len(data["decisions"]) == 1
        assert len(data["commitments"]) == 1

    def test_extract_llm_failure(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.side_effect = Exception("LLM down")

        resp = client.post(
            "/api/v1/tools/extract",
            json={"content": "Some meeting notes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action_items"] == []


# ================================================================
# POST /tools/ask
# ================================================================

class TestAsk:

    def test_ask_with_context(self, client, mock_deps):
        repo, llm, _ = mock_deps
        repo.get_events.return_value = [
            _make_event("Q3 budget is $50,000", topics=["budget", "Q3"]),
        ]
        llm.generate.return_value = '{"answer": "The Q3 budget is $50,000."}'

        resp = client.post(
            "/api/v1/tools/ask",
            json={"query": "What is the Q3 budget?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "50,000" in data["answer"]
        assert len(data["sources"]) > 0

    def test_ask_no_matching_events(self, client, mock_deps):
        repo, llm, _ = mock_deps
        repo.get_events.return_value = []

        resp = client.post(
            "/api/v1/tools/ask",
            json={"query": "Something with no context"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data

    def test_ask_llm_failure(self, client, mock_deps):
        repo, llm, _ = mock_deps
        repo.get_events.return_value = [_make_event()]
        llm.generate.side_effect = Exception("LLM down")

        resp = client.post(
            "/api/v1/tools/ask",
            json={"query": "test query"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
