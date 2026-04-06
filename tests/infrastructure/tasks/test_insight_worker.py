"""Unit tests for the insight worker — freshness, dormancy, commitments, briefings."""

import math
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest

from src.infrastructure.tasks.insight_worker import (
    COMMITMENT_GRACE_HOURS,
    DECAY_RATE,
    PERSON_DORMANCY_DAYS,
    PROJECT_DORMANCY_DAYS,
    check_overdue_commitments,
    compute_freshness,
    generate_morning_briefing,
    generate_weekly_digest,
    update_freshness_scores,
)


# ---- Helpers ----


def _make_person_model(user_id, name="Alice", days_since_active=0, **kwargs):
    """Create a mock PersonProfileModel."""
    now = datetime.now()
    model = MagicMock()
    model.user_id = user_id
    model.name = name
    model.last_activity_at = kwargs.get("last_activity_at", now - timedelta(days=days_since_active))
    model.last_seen = kwargs.get("last_seen", now - timedelta(days=days_since_active))
    model.created_at = kwargs.get("created_at", now - timedelta(days=60))
    model.freshness_score = kwargs.get("freshness_score", 1.0)
    model.dormancy_days = kwargs.get("dormancy_days", 0)
    return model


def _make_project_model(user_id, title="Project Alpha", days_since_active=0, **kwargs):
    """Create a mock ProjectModel."""
    now = datetime.now()
    model = MagicMock()
    model.user_id = user_id
    model.title = title
    model.status = kwargs.get("status", "active")
    model.last_activity_at = kwargs.get("last_activity_at", now - timedelta(days=days_since_active))
    model.updated_at = kwargs.get("updated_at", now - timedelta(days=days_since_active))
    model.created_at = kwargs.get("created_at", now - timedelta(days=60))
    model.dormancy_days = kwargs.get("dormancy_days", 0)
    return model


def _make_commitment_model(user_id, days_overdue=2, **kwargs):
    """Create a mock CommitmentModel."""
    now = datetime.now()
    model = MagicMock()
    model.id = kwargs.get("id", uuid4())
    model.user_id = user_id
    model.description = kwargs.get("description", "Send report to Bob")
    model.due_date = kwargs.get("due_date", now - timedelta(days=days_overdue))
    model.status = kwargs.get("status", "open")
    return model


# ---- Fixtures ----


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def mock_session():
    """Create a mock async session that supports context-manager protocol."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
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
def mock_llm_service():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="A concise morning briefing summary.")
    return llm


# ======================================================================
# compute_freshness — pure function tests
# ======================================================================


class TestComputeFreshness:
    """Tests for the compute_freshness pure function."""

    def test_zero_days_returns_approximately_one(self):
        """Freshness at 0 days since last activity should be ~1.0."""
        result = compute_freshness(0.0)
        assert result == pytest.approx(1.0)

    def test_half_life_at_14_days(self):
        """With DECAY_RATE=0.05, freshness at 14 days should be ~0.5."""
        result = compute_freshness(14.0)
        expected = math.exp(-0.05 * 14)  # ~0.4966
        assert result == pytest.approx(expected, abs=0.01)

    def test_30_days_decay(self):
        """Freshness at 30 days should be ~0.22."""
        result = compute_freshness(30.0)
        expected = math.exp(-0.05 * 30)  # ~0.2231
        assert result == pytest.approx(expected, abs=0.01)

    def test_large_days_approaches_zero(self):
        """After many days, freshness should approach 0."""
        result = compute_freshness(200.0)
        assert result < 0.01

    def test_negative_days_treated_as_zero(self):
        """Negative days should be clamped to 0."""
        result = compute_freshness(-5.0)
        assert result == pytest.approx(1.0)

    def test_link_boost_adds_to_score(self):
        """Link boost should be added to the base decay score."""
        base = compute_freshness(14.0, link_boost=0.0)
        boosted = compute_freshness(14.0, link_boost=0.1)
        assert boosted == pytest.approx(base + 0.1)

    def test_link_boost_capped_at_one(self):
        """Total freshness with link_boost should not exceed 1.0."""
        result = compute_freshness(0.0, link_boost=0.5)
        assert result == 1.0

    def test_result_never_below_zero(self):
        """Freshness should never be negative."""
        result = compute_freshness(1000.0, link_boost=-0.5)
        assert result >= 0.0

    def test_link_boost_recovers_stale_entity(self):
        """A high link boost can bring a stale entity back to reasonable freshness."""
        result = compute_freshness(30.0, link_boost=0.2)
        expected = math.exp(-0.05 * 30) + 0.2
        assert result == pytest.approx(expected, abs=0.01)
        assert result > 0.4


# ======================================================================
# update_freshness_scores
# ======================================================================


class TestUpdateFreshnessScores:
    """Tests for update_freshness_scores with mocked DB."""

    async def test_recent_person_has_high_freshness(self, user_id, mock_database, mock_session):
        """A person active today should have freshness close to 1.0."""
        person = _make_person_model(user_id, name="Alice", days_since_active=0)

        # Mock people query
        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = [person]
        people_result.scalars.return_value = people_scalars

        # Mock projects query (empty)
        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = []
        projects_result.scalars.return_value = projects_scalars

        # Mock connection count
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_session.execute.side_effect = [people_result, count_result, projects_result]

        stats = await update_freshness_scores(mock_database, user_id)

        assert stats["people_updated"] == 1
        assert stats["dormant_people"] == 0
        assert person.freshness_score >= 0.9

    async def test_old_person_is_marked_dormant(self, user_id, mock_database, mock_session):
        """A person inactive for >21 days should be marked dormant."""
        person = _make_person_model(user_id, name="Bob", days_since_active=30)

        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = [person]
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = []
        projects_result.scalars.return_value = projects_scalars

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_session.execute.side_effect = [people_result, count_result, projects_result]

        stats = await update_freshness_scores(mock_database, user_id)

        assert stats["dormant_people"] == 1
        assert person.dormancy_days == 30

    async def test_project_inactive_14_days_is_dormant(self, user_id, mock_database, mock_session):
        """A project inactive for >14 days should be flagged as dormant."""
        project = _make_project_model(user_id, title="Beta", days_since_active=20)

        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = []
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = [project]
        projects_result.scalars.return_value = projects_scalars

        mock_session.execute.side_effect = [people_result, projects_result]

        stats = await update_freshness_scores(mock_database, user_id)

        assert stats["projects_updated"] == 1
        assert stats["dormant_projects"] == 1
        assert project.dormancy_days == 20

    async def test_active_project_is_not_dormant(self, user_id, mock_database, mock_session):
        """A project active within 14 days should NOT be dormant."""
        project = _make_project_model(user_id, title="Gamma", days_since_active=5)

        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = []
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = [project]
        projects_result.scalars.return_value = projects_scalars

        mock_session.execute.side_effect = [people_result, projects_result]

        stats = await update_freshness_scores(mock_database, user_id)

        assert stats["dormant_projects"] == 0
        assert project.dormancy_days == 0

    async def test_connection_count_provides_link_boost(self, user_id, mock_database, mock_session):
        """Recent connections should boost a person's freshness score."""
        person = _make_person_model(user_id, name="Carol", days_since_active=14)

        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = [person]
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = []
        projects_result.scalars.return_value = projects_scalars

        # 5 recent connections => link_boost = min(0.2, 5 * 0.02) = 0.1
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        mock_session.execute.side_effect = [people_result, count_result, projects_result]

        stats = await update_freshness_scores(mock_database, user_id)

        base = math.exp(-DECAY_RATE * 14)
        boosted = base + 0.1
        assert person.freshness_score == pytest.approx(round(boosted, 4), abs=0.01)

    async def test_commits_session(self, user_id, mock_database, mock_session):
        """Session should be committed after updating scores."""
        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = []
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = []
        projects_result.scalars.return_value = projects_scalars

        mock_session.execute.side_effect = [people_result, projects_result]

        await update_freshness_scores(mock_database, user_id)

        mock_session.commit.assert_awaited_once()


# ======================================================================
# check_overdue_commitments
# ======================================================================


class TestCheckOverdueCommitments:
    """Tests for check_overdue_commitments."""

    async def test_overdue_commitment_is_flagged(self, user_id, mock_database, mock_session):
        """A commitment past due_date should be marked as 'overdue'."""
        commitment = _make_commitment_model(user_id, days_overdue=3, description="Send report")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [commitment]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        overdue = await check_overdue_commitments(mock_database, user_id)

        assert len(overdue) == 1
        assert overdue[0]["description"] == "Send report"
        assert overdue[0]["days_overdue"] >= 2
        assert commitment.status == "overdue"

    async def test_no_overdue_returns_empty_list(self, user_id, mock_database, mock_session):
        """When no commitments are overdue, return an empty list."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        overdue = await check_overdue_commitments(mock_database, user_id)

        assert overdue == []

    async def test_multiple_overdue_commitments(self, user_id, mock_database, mock_session):
        """Multiple overdue commitments should all be returned."""
        c1 = _make_commitment_model(user_id, days_overdue=5, description="Task A")
        c2 = _make_commitment_model(user_id, days_overdue=2, description="Task B")

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [c1, c2]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        overdue = await check_overdue_commitments(mock_database, user_id)

        assert len(overdue) == 2
        descriptions = {o["description"] for o in overdue}
        assert "Task A" in descriptions
        assert "Task B" in descriptions

    async def test_overdue_commitment_has_correct_structure(self, user_id, mock_database, mock_session):
        """Each overdue item should have id, description, due_date, days_overdue keys."""
        commitment = _make_commitment_model(user_id, days_overdue=3)

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [commitment]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        overdue = await check_overdue_commitments(mock_database, user_id)

        item = overdue[0]
        assert "id" in item
        assert "description" in item
        assert "due_date" in item
        assert "days_overdue" in item

    async def test_session_is_committed(self, user_id, mock_database, mock_session):
        """Session should be committed after flagging overdue commitments."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        mock_session.execute.return_value = result_mock

        await check_overdue_commitments(mock_database, user_id)

        mock_session.commit.assert_awaited_once()


# ======================================================================
# generate_morning_briefing
# ======================================================================


class TestGenerateMorningBriefing:
    """Tests for generate_morning_briefing."""

    async def test_briefing_has_required_keys(self, user_id, mock_database, mock_session, mock_llm_service):
        """Briefing dict should contain all expected keys."""
        # Set up all the mocks needed for the full briefing pipeline
        # check_overdue_commitments mock
        overdue_scalars = MagicMock()
        overdue_scalars.all.return_value = []
        overdue_result = MagicMock()
        overdue_result.scalars.return_value = overdue_scalars

        # update_freshness_scores mocks (people, projects)
        people_result = MagicMock()
        people_scalars = MagicMock()
        people_scalars.all.return_value = []
        people_result.scalars.return_value = people_scalars

        projects_result = MagicMock()
        projects_scalars = MagicMock()
        projects_scalars.all.return_value = []
        projects_result.scalars.return_value = projects_scalars

        # dormant people and projects queries
        dormant_people_result = MagicMock()
        dormant_people_scalars = MagicMock()
        dormant_people_scalars.all.return_value = []
        dormant_people_result.scalars.return_value = dormant_people_scalars

        dormant_projects_result = MagicMock()
        dormant_projects_scalars = MagicMock()
        dormant_projects_scalars.all.return_value = []
        dormant_projects_result.scalars.return_value = dormant_projects_scalars

        # The function calls session multiple times across subfunctions.
        # We patch at a higher level.
        with patch(
            "src.infrastructure.tasks.insight_worker.check_overdue_commitments",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.infrastructure.tasks.insight_worker.update_freshness_scores",
            new_callable=AsyncMock,
            return_value={"people_updated": 0, "projects_updated": 0, "dormant_people": 0, "dormant_projects": 0},
        ), patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            MockRepo.return_value = repo_instance

            mock_session.execute.side_effect = [dormant_people_result, dormant_projects_result]

            briefing = await generate_morning_briefing(mock_database, mock_llm_service, user_id)

        assert "date" in briefing
        assert "overdue_commitments" in briefing
        assert "stale_people" in briefing
        assert "stale_projects" in briefing
        assert "today_event_count" in briefing
        assert "attention_items" in briefing

    async def test_briefing_includes_overdue_items(self, user_id, mock_database, mock_session, mock_llm_service):
        """When there are overdue commitments, they appear in the briefing."""
        overdue_item = {"id": str(uuid4()), "description": "Call Bob", "due_date": "2026-04-01", "days_overdue": 5}

        with patch(
            "src.infrastructure.tasks.insight_worker.check_overdue_commitments",
            new_callable=AsyncMock,
            return_value=[overdue_item],
        ), patch(
            "src.infrastructure.tasks.insight_worker.update_freshness_scores",
            new_callable=AsyncMock,
            return_value={"people_updated": 0, "projects_updated": 0, "dormant_people": 0, "dormant_projects": 0},
        ), patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            MockRepo.return_value = repo_instance

            dormant_result = MagicMock()
            dormant_scalars = MagicMock()
            dormant_scalars.all.return_value = []
            dormant_result.scalars.return_value = dormant_scalars
            mock_session.execute.side_effect = [dormant_result, dormant_result]

            briefing = await generate_morning_briefing(mock_database, mock_llm_service, user_id)

        assert len(briefing["overdue_commitments"]) == 1
        assert any("overdue" in item for item in briefing["attention_items"])

    async def test_briefing_includes_stale_people(self, user_id, mock_database, mock_session, mock_llm_service):
        """Dormant people should appear in the stale_people list."""
        stale_person = MagicMock()
        stale_person.name = "Eve"
        stale_person.dormancy_days = 30
        stale_person.last_seen = datetime.now() - timedelta(days=30)

        with patch(
            "src.infrastructure.tasks.insight_worker.check_overdue_commitments",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "src.infrastructure.tasks.insight_worker.update_freshness_scores",
            new_callable=AsyncMock,
            return_value={"people_updated": 1, "projects_updated": 0, "dormant_people": 1, "dormant_projects": 0},
        ), patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            MockRepo.return_value = repo_instance

            dormant_people_result = MagicMock()
            dormant_people_scalars = MagicMock()
            dormant_people_scalars.all.return_value = [stale_person]
            dormant_people_result.scalars.return_value = dormant_people_scalars

            dormant_projects_result = MagicMock()
            dormant_projects_scalars = MagicMock()
            dormant_projects_scalars.all.return_value = []
            dormant_projects_result.scalars.return_value = dormant_projects_scalars

            mock_session.execute.side_effect = [dormant_people_result, dormant_projects_result]

            briefing = await generate_morning_briefing(mock_database, mock_llm_service, user_id)

        assert len(briefing["stale_people"]) == 1
        assert briefing["stale_people"][0]["name"] == "Eve"
        assert any("Eve" in item for item in briefing["attention_items"])

    async def test_briefing_llm_failure_provides_fallback_summary(self, user_id, mock_database, mock_session):
        """When LLM fails, the briefing should still have a summary."""
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = Exception("LLM down")

        with patch(
            "src.infrastructure.tasks.insight_worker.check_overdue_commitments",
            new_callable=AsyncMock,
            return_value=[{"id": "1", "description": "x", "due_date": None, "days_overdue": 0}],
        ), patch(
            "src.infrastructure.tasks.insight_worker.update_freshness_scores",
            new_callable=AsyncMock,
            return_value={"people_updated": 0, "projects_updated": 0, "dormant_people": 0, "dormant_projects": 0},
        ), patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = [MagicMock()]  # trigger LLM path
            MockRepo.return_value = repo_instance

            dormant_result = MagicMock()
            dormant_scalars = MagicMock()
            dormant_scalars.all.return_value = []
            dormant_result.scalars.return_value = dormant_scalars
            mock_session.execute.side_effect = [dormant_result, dormant_result]

            briefing = await generate_morning_briefing(mock_database, failing_llm, user_id)

        assert "summary" in briefing
        assert "attention" in briefing["summary"].lower()


# ======================================================================
# generate_weekly_digest
# ======================================================================


class TestGenerateWeeklyDigest:
    """Tests for generate_weekly_digest."""

    async def test_digest_has_required_keys(self, user_id, mock_database, mock_llm_service):
        """Weekly digest should have all expected structural keys."""
        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, mock_llm_service, user_id)

        assert "period" in digest
        assert "total_events" in digest
        assert "sources" in digest
        assert "top_topics" in digest
        assert "new_connections" in digest
        assert "active_people" in digest
        assert "people_count" in digest
        assert "summary" in digest

    async def test_digest_aggregates_topics(self, user_id, mock_database, mock_llm_service):
        """Topics should be aggregated and sorted by count."""
        from src.domain.entities.context_event import ContextEvent

        now = datetime.now()
        events = [
            ContextEvent(
                id=uuid4(), user_id=user_id, source="email", event_type="message",
                content="test", timestamp=now, topics=["python", "testing"],
                created_at=now,
            ),
            ContextEvent(
                id=uuid4(), user_id=user_id, source="calendar", event_type="meeting",
                content="test", timestamp=now, topics=["python", "design"],
                created_at=now,
            ),
        ]

        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, mock_llm_service, user_id)

        topic_map = {t["topic"]: t["count"] for t in digest["top_topics"]}
        assert topic_map["python"] == 2
        assert topic_map["testing"] == 1
        assert topic_map["design"] == 1

    async def test_digest_counts_sources(self, user_id, mock_database, mock_llm_service):
        """Source breakdown should count events per source."""
        from src.domain.entities.context_event import ContextEvent

        now = datetime.now()
        events = [
            ContextEvent(id=uuid4(), user_id=user_id, source="email", event_type="message",
                         content="a", timestamp=now, created_at=now),
            ContextEvent(id=uuid4(), user_id=user_id, source="email", event_type="message",
                         content="b", timestamp=now, created_at=now),
            ContextEvent(id=uuid4(), user_id=user_id, source="calendar", event_type="meeting",
                         content="c", timestamp=now, created_at=now),
        ]

        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, mock_llm_service, user_id)

        assert digest["sources"]["email"] == 2
        assert digest["sources"]["calendar"] == 1
        assert digest["total_events"] == 3

    async def test_digest_llm_failure_provides_fallback_summary(self, user_id, mock_database):
        """When LLM fails, the digest should still have a summary string."""
        failing_llm = AsyncMock()
        failing_llm.generate.side_effect = Exception("LLM error")

        from src.domain.entities.context_event import ContextEvent

        now = datetime.now()
        events = [
            ContextEvent(id=uuid4(), user_id=user_id, source="email", event_type="message",
                         content="a", timestamp=now, created_at=now),
        ]

        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, failing_llm, user_id)

        assert "summary" in digest
        assert "1 events" in digest["summary"] or "1" in digest["summary"]

    async def test_digest_no_events(self, user_id, mock_database, mock_llm_service):
        """With no events, digest should still have valid structure."""
        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, mock_llm_service, user_id)

        assert digest["total_events"] == 0
        assert digest["top_topics"] == []
        assert digest["sources"] == {}

    async def test_digest_counts_new_connections(self, user_id, mock_database, mock_llm_service):
        """New connections discovered within the digest period should be counted."""
        from src.domain.entities.context_event import Connection

        now = datetime.now()
        conns = [
            Connection(
                id=uuid4(), user_id=user_id,
                source_event_id=uuid4(), target_event_id=uuid4(),
                connection_type="same_person", strength=0.8,
                discovered_at=now - timedelta(days=2),
                method="entity_match",
            ),
            Connection(
                id=uuid4(), user_id=user_id,
                source_event_id=uuid4(), target_event_id=uuid4(),
                connection_type="temporal", strength=0.6,
                discovered_at=now - timedelta(days=10),  # outside 7-day window
                method="temporal_cluster",
            ),
        ]

        with patch(
            "src.infrastructure.tasks.insight_worker.ContextEventRepository"
        ) as MockRepo, patch(
            "src.infrastructure.tasks.insight_worker._log_resurfacing",
            new_callable=AsyncMock,
        ):
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            repo_instance.get_people.return_value = []
            repo_instance.get_connections.return_value = conns
            MockRepo.return_value = repo_instance

            digest = await generate_weekly_digest(mock_database, mock_llm_service, user_id)

        # Only the connection within the last 7 days should be counted
        assert digest["new_connections"] == 1
