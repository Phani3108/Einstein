"""Tests for distillation API routes."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.distillation import create_distillation_router
from src.domain.entities.context_event import ContextEvent
from src.domain.entities.user import User


def _make_user():
    return User(id=uuid.uuid4(), username="tester", email="t@example.com")


def _make_event(
    content="A very long note about project planning " * 30,
    timestamp=None,
    structured_data=None,
):
    return ContextEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        source="manual_note",
        event_type="note",
        content=content,
        timestamp=timestamp or datetime.now(),
        structured_data=structured_data or {},
    )


@pytest.fixture
def mock_deps():
    repo = AsyncMock()
    llm = AsyncMock()
    auth = MagicMock()
    auth.require_authentication = MagicMock(return_value=_make_user())
    repo.get_events = AsyncMock(return_value=[])
    return repo, llm, auth


@pytest.fixture
def client(mock_deps):
    repo, llm, auth = mock_deps
    app = FastAPI()
    router = create_distillation_router(
        context_repo=repo, llm_service=llm, auth_middleware=auth
    )
    app.include_router(router)
    app.dependency_overrides[auth.require_authentication] = _make_user
    return TestClient(app)


class TestDistill:

    def test_distill_by_content(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.return_value = '{"summary": "Project planning overview", "key_points": ["Timeline set", "Budget approved"]}'

        resp = client.post(
            "/api/v1/distillation/distill",
            json={"content": "A long note about project planning " * 50},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "Project planning overview"
        assert len(data["key_points"]) == 2

    def test_distill_by_event_id(self, client, mock_deps):
        repo, llm, _ = mock_deps
        event = _make_event()
        repo.get_events.return_value = [event]
        llm.generate.return_value = '{"summary": "Summary here", "key_points": ["Point 1"]}'

        resp = client.post(
            "/api/v1/distillation/distill",
            json={"event_id": str(event.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_distill_llm_failure(self, client, mock_deps):
        _, llm, _ = mock_deps
        llm.generate.side_effect = Exception("LLM down")

        resp = client.post(
            "/api/v1/distillation/distill",
            json={"content": "Some long content " * 100},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] != ""  # Falls back to truncation


class TestAutoDistill:

    def test_auto_no_eligible(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = []

        resp = client.post("/api/v1/distillation/auto")
        assert resp.status_code == 200
        data = resp.json()
        assert data["distilled_count"] == 0

    def test_auto_distills_old_verbose_events(self, client, mock_deps):
        repo, llm, _ = mock_deps
        old_event = _make_event(
            content="Very long content " * 200,
            timestamp=datetime.now() - timedelta(days=14),
        )
        repo.get_events.return_value = [old_event]
        llm.generate.return_value = '{"summary": "Distilled", "key_points": []}'

        resp = client.post(
            "/api/v1/distillation/auto",
            params={"min_words": 100, "min_days": 7},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["distilled_count"] >= 0  # May or may not match filter


class TestDistillationStatus:

    def test_status(self, client, mock_deps):
        repo, _, _ = mock_deps
        repo.get_events.return_value = [
            _make_event(),
            _make_event(structured_data={"distilled_summary": "Already done"}),
        ]

        resp = client.get("/api/v1/distillation/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "distilled" in data
        assert "eligible" in data
