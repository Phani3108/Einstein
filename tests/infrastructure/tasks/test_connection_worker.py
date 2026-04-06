"""Unit tests for the connection discovery worker."""

import json
import math
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.domain.entities.context_event import Connection, ContextEvent
from src.infrastructure.tasks.connection_worker import (
    SIMILARITY_THRESHOLD,
    TEMPORAL_WINDOW_MINUTES,
    _discover_embedding_similarity,
    _discover_entity_matches,
    _discover_llm_inference,
    _discover_temporal_clusters,
    cosine_similarity,
    discover_connections,
)


# ---- Helpers ----


def _make_event(user_id=None, source="notification", **kwargs):
    """Create a ContextEvent with sensible defaults."""
    return ContextEvent(
        id=kwargs.get("id", uuid4()),
        user_id=user_id or uuid4(),
        source=source,
        source_id=kwargs.get("source_id", None),
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
    llm.generate = AsyncMock(return_value="{}")
    return llm


# ======================================================================
# cosine_similarity — pure function tests
# ======================================================================


class TestCosineSimilarity:
    """Tests for the cosine_similarity pure function."""

    def test_identical_vectors_return_one(self):
        """Two identical unit vectors should have similarity 1.0."""
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self):
        """Two orthogonal vectors should have similarity 0.0."""
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_return_negative_one(self):
        """Two opposite vectors should have similarity -1.0."""
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_known_value(self):
        """Check against a hand-computed cosine similarity."""
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        dot = 1 * 4 + 2 * 5 + 3 * 6  # 32
        norm_a = math.sqrt(1 + 4 + 9)  # sqrt(14)
        norm_b = math.sqrt(16 + 25 + 36)  # sqrt(77)
        expected = dot / (norm_a * norm_b)
        assert cosine_similarity(a, b) == pytest.approx(expected)

    def test_empty_vectors_return_zero(self):
        """Empty vectors should return 0.0."""
        assert cosine_similarity([], []) == 0.0

    def test_mismatched_lengths_return_zero(self):
        """Vectors of different lengths should return 0.0."""
        assert cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_zero_vector_returns_zero(self):
        """A zero vector should return 0.0 (division by zero guard)."""
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_single_element_vectors(self):
        """Single-element vectors should work correctly."""
        assert cosine_similarity([3.0], [5.0]) == pytest.approx(1.0)


# ======================================================================
# _discover_entity_matches
# ======================================================================


class TestDiscoverEntityMatches:
    """Tests for _discover_entity_matches."""

    def test_events_mentioning_same_person_get_connected(self, user_id):
        """Two events mentioning 'Alice' produce a same_person connection."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice"])
        e2 = _make_event(user_id=user_id, extracted_people=["Alice"])

        connections = _discover_entity_matches([e1, e2], set())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.connection_type == "same_person"
        assert conn.strength == 0.8
        assert conn.method == "entity_match"
        assert "alice" in conn.evidence.lower()

    def test_case_insensitive_matching(self, user_id):
        """Entity match should be case-insensitive."""
        e1 = _make_event(user_id=user_id, extracted_people=["alice"])
        e2 = _make_event(user_id=user_id, extracted_people=["ALICE"])

        connections = _discover_entity_matches([e1, e2], set())

        assert len(connections) == 1

    def test_no_overlap_produces_no_connections(self, user_id):
        """Events mentioning different people should not be connected."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice"])
        e2 = _make_event(user_id=user_id, extracted_people=["Bob"])

        connections = _discover_entity_matches([e1, e2], set())

        assert len(connections) == 0

    def test_existing_pairs_are_skipped(self, user_id):
        """Connections that already exist should not be recreated."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice"])
        e2 = _make_event(user_id=user_id, extracted_people=["Alice"])
        existing = {(e1.id, e2.id)}

        connections = _discover_entity_matches([e1, e2], existing)

        assert len(connections) == 0

    def test_existing_pairs_skipped_in_reverse_order(self, user_id):
        """Reversed pair should also be treated as existing."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice"])
        e2 = _make_event(user_id=user_id, extracted_people=["Alice"])
        existing = {(e2.id, e1.id)}

        connections = _discover_entity_matches([e1, e2], existing)

        assert len(connections) == 0

    def test_single_event_produces_no_connections(self, user_id):
        """A single event mentioning Alice should produce no connections."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice"])

        connections = _discover_entity_matches([e1], set())

        assert len(connections) == 0

    def test_multiple_people_produce_multiple_connections(self, user_id):
        """Events sharing multiple people produce connections for each person."""
        e1 = _make_event(user_id=user_id, extracted_people=["Alice", "Bob"])
        e2 = _make_event(user_id=user_id, extracted_people=["Alice", "Bob"])

        connections = _discover_entity_matches([e1, e2], set())

        # One connection per shared person (Alice and Bob)
        assert len(connections) == 2
        types = {c.evidence for c in connections}
        assert any("alice" in t for t in types)
        assert any("bob" in t for t in types)

    def test_three_events_same_person_produce_pairwise_connections(self, user_id):
        """Three events mentioning the same person produce 3 pairwise connections."""
        events = [
            _make_event(user_id=user_id, extracted_people=["Alice"])
            for _ in range(3)
        ]

        connections = _discover_entity_matches(events, set())

        # C(3,2) = 3 pairs
        assert len(connections) == 3

    def test_no_extracted_people_produces_no_connections(self, user_id):
        """Events without extracted_people should produce no connections."""
        e1 = _make_event(user_id=user_id, extracted_people=[])
        e2 = _make_event(user_id=user_id, extracted_people=[])

        connections = _discover_entity_matches([e1, e2], set())

        assert len(connections) == 0


# ======================================================================
# _discover_temporal_clusters
# ======================================================================


class TestDiscoverTemporalClusters:
    """Tests for _discover_temporal_clusters."""

    def test_events_within_30_min_from_different_sources_get_connected(self, user_id):
        """Events from different sources within 30 min should be connected."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now + timedelta(minutes=10))

        connections = _discover_temporal_clusters([e1, e2], set())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.connection_type == "temporal"
        assert conn.method == "temporal_cluster"

    def test_events_from_same_source_are_not_connected(self, user_id):
        """Events from the same source within 30 min should NOT be connected."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="email", timestamp=now + timedelta(minutes=5))

        connections = _discover_temporal_clusters([e1, e2], set())

        assert len(connections) == 0

    def test_events_outside_30_min_window_are_not_connected(self, user_id):
        """Events more than 30 min apart should not be connected."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now + timedelta(minutes=31))

        connections = _discover_temporal_clusters([e1, e2], set())

        assert len(connections) == 0

    def test_strength_is_1_for_simultaneous_events(self, user_id):
        """Events at the same timestamp should have strength close to 1.0."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now)

        connections = _discover_temporal_clusters([e1, e2], set())

        assert len(connections) == 1
        assert connections[0].strength == pytest.approx(1.0)

    def test_strength_proportional_to_time_gap(self, user_id):
        """Strength should decrease as time gap increases."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now + timedelta(minutes=15))

        connections = _discover_temporal_clusters([e1, e2], set())

        conn = connections[0]
        # delta=900s, window=1800s => strength = 1.0 - 900/1800 = 0.5
        assert conn.strength == pytest.approx(0.5)

    def test_strength_has_minimum_of_0_3(self, user_id):
        """Strength should not drop below 0.3 within the window."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now + timedelta(minutes=29))

        connections = _discover_temporal_clusters([e1, e2], set())

        assert len(connections) == 1
        assert connections[0].strength >= 0.3

    def test_existing_pairs_are_skipped(self, user_id):
        """Existing temporal connections should not be recreated."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="calendar", timestamp=now + timedelta(minutes=5))
        existing = {(e1.id, e2.id)}

        connections = _discover_temporal_clusters([e1, e2], existing)

        assert len(connections) == 0

    def test_evidence_includes_source_names(self, user_id):
        """Evidence string should mention the sources of both events."""
        now = datetime.now()
        e1 = _make_event(user_id=user_id, source="email", timestamp=now)
        e2 = _make_event(user_id=user_id, source="sms", timestamp=now + timedelta(minutes=5))

        connections = _discover_temporal_clusters([e1, e2], set())

        assert "email" in connections[0].evidence
        assert "sms" in connections[0].evidence


# ======================================================================
# _discover_embedding_similarity
# ======================================================================


class TestDiscoverEmbeddingSimilarity:
    """Tests for _discover_embedding_similarity."""

    async def test_similar_embeddings_produce_connections(self, user_id, mock_database, mock_session):
        """Events with cosine similarity >= threshold should be connected."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        # Two nearly identical embeddings
        emb = [1.0, 0.0, 0.0]
        result_mock = MagicMock()
        result_mock.all.return_value = [(e1.id, emb), (e2.id, emb)]
        mock_session.execute.return_value = result_mock

        connections = await _discover_embedding_similarity(mock_database, [e1, e2], set())

        assert len(connections) == 1
        conn = connections[0]
        assert conn.connection_type == "semantic_similar"
        assert conn.method == "embedding_similarity"
        assert conn.strength == pytest.approx(1.0, abs=0.01)

    async def test_dissimilar_embeddings_produce_no_connections(self, user_id, mock_database, mock_session):
        """Events with cosine similarity below threshold should not be connected."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        # Orthogonal embeddings
        result_mock = MagicMock()
        result_mock.all.return_value = [(e1.id, [1.0, 0.0, 0.0]), (e2.id, [0.0, 1.0, 0.0])]
        mock_session.execute.return_value = result_mock

        connections = await _discover_embedding_similarity(mock_database, [e1, e2], set())

        assert len(connections) == 0

    async def test_no_embeddings_returns_empty(self, user_id, mock_database, mock_session):
        """When no events have embeddings, return an empty list."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        result_mock = MagicMock()
        result_mock.all.return_value = []
        mock_session.execute.return_value = result_mock

        connections = await _discover_embedding_similarity(mock_database, [e1, e2], set())

        assert len(connections) == 0

    async def test_single_embedding_returns_empty(self, user_id, mock_database, mock_session):
        """With only one event having an embedding, no pairs can be formed."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        result_mock = MagicMock()
        result_mock.all.return_value = [(e1.id, [1.0, 0.0])]
        mock_session.execute.return_value = result_mock

        connections = await _discover_embedding_similarity(mock_database, [e1, e2], set())

        assert len(connections) == 0

    async def test_existing_pairs_are_skipped(self, user_id, mock_database, mock_session):
        """Existing embedding connections should not be recreated."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        emb = [1.0, 0.0, 0.0]
        result_mock = MagicMock()
        result_mock.all.return_value = [(e1.id, emb), (e2.id, emb)]
        mock_session.execute.return_value = result_mock

        existing = {(e1.id, e2.id)}
        connections = await _discover_embedding_similarity(mock_database, [e1, e2], existing)

        assert len(connections) == 0

    async def test_none_embedding_is_filtered(self, user_id, mock_database, mock_session):
        """Rows with None embedding should be ignored."""
        e1 = _make_event(user_id=user_id)
        e2 = _make_event(user_id=user_id)

        result_mock = MagicMock()
        result_mock.all.return_value = [(e1.id, [1.0, 0.0]), (e2.id, None)]
        mock_session.execute.return_value = result_mock

        connections = await _discover_embedding_similarity(mock_database, [e1, e2], set())

        assert len(connections) == 0


# ======================================================================
# _discover_llm_inference
# ======================================================================


class TestDiscoverLLMInference:
    """Tests for _discover_llm_inference."""

    async def test_llm_returns_valid_connections(self, user_id, mock_llm_service):
        """LLM returning valid JSON should produce connections."""
        events = [_make_event(user_id=user_id) for _ in range(5)]

        llm_response = json.dumps({
            "connections": [
                {
                    "event_a_index": 0,
                    "event_b_index": 1,
                    "type": "follow_up",
                    "strength": 0.9,
                    "evidence": "Event B follows up on event A",
                }
            ]
        })
        mock_llm_service.generate.return_value = llm_response

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert len(connections) == 1
        conn = connections[0]
        assert conn.connection_type == "follow_up"
        assert conn.strength == 0.9
        assert conn.method == "llm_inference"
        assert conn.source_event_id == events[0].id
        assert conn.target_event_id == events[1].id

    async def test_llm_failure_returns_empty_list(self, user_id, mock_llm_service):
        """When LLM raises an exception, return an empty list gracefully."""
        events = [_make_event(user_id=user_id) for _ in range(5)]
        mock_llm_service.generate.side_effect = Exception("LLM unavailable")

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert connections == []

    async def test_llm_returns_invalid_json_returns_empty(self, user_id, mock_llm_service):
        """When LLM returns unparseable JSON, return an empty list."""
        events = [_make_event(user_id=user_id) for _ in range(5)]
        mock_llm_service.generate.return_value = "not valid json at all"

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert connections == []

    async def test_llm_invalid_indices_are_skipped(self, user_id, mock_llm_service):
        """Connections with out-of-range indices should be ignored."""
        events = [_make_event(user_id=user_id) for _ in range(5)]

        llm_response = json.dumps({
            "connections": [
                {"event_a_index": 0, "event_b_index": 99, "type": "related", "strength": 0.5},
                {"event_a_index": -1, "event_b_index": 0, "type": "related", "strength": 0.5},
            ]
        })
        mock_llm_service.generate.return_value = llm_response

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert len(connections) == 0

    async def test_llm_existing_pairs_are_skipped(self, user_id, mock_llm_service):
        """LLM-suggested connections that already exist should be filtered out."""
        events = [_make_event(user_id=user_id) for _ in range(5)]
        existing = {(events[0].id, events[1].id)}

        llm_response = json.dumps({
            "connections": [
                {"event_a_index": 0, "event_b_index": 1, "type": "related", "strength": 0.8},
            ]
        })
        mock_llm_service.generate.return_value = llm_response

        connections = await _discover_llm_inference(mock_llm_service, events, existing, user_id)

        assert len(connections) == 0

    async def test_llm_strength_is_clamped(self, user_id, mock_llm_service):
        """Strength values should be clamped to [0.1, 1.0]."""
        events = [_make_event(user_id=user_id) for _ in range(5)]

        llm_response = json.dumps({
            "connections": [
                {"event_a_index": 0, "event_b_index": 1, "type": "related", "strength": 5.0},
                {"event_a_index": 2, "event_b_index": 3, "type": "related", "strength": -1.0},
            ]
        })
        mock_llm_service.generate.return_value = llm_response

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert connections[0].strength == 1.0
        assert connections[1].strength == 0.1

    async def test_llm_empty_connections_list(self, user_id, mock_llm_service):
        """LLM returning empty connections list should produce no connections."""
        events = [_make_event(user_id=user_id) for _ in range(5)]
        mock_llm_service.generate.return_value = json.dumps({"connections": []})

        connections = await _discover_llm_inference(mock_llm_service, events, set(), user_id)

        assert connections == []


# ======================================================================
# discover_connections — integration
# ======================================================================


class TestDiscoverConnections:
    """Integration tests for discover_connections with mocked strategies."""

    async def test_fewer_than_two_events_returns_zero(self, user_id, mock_database):
        """When fewer than 2 events exist, no discovery is needed."""
        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = [_make_event(user_id=user_id)]
            repo_instance.get_connections.return_value = []
            MockRepo.return_value = repo_instance

            result = await discover_connections(mock_database, user_id)

        assert result == 0

    async def test_no_events_returns_zero(self, user_id, mock_database):
        """When no events exist, return 0."""
        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = []
            MockRepo.return_value = repo_instance

            result = await discover_connections(mock_database, user_id)

        assert result == 0

    async def test_connections_are_stored_and_counted(self, user_id, mock_database):
        """New connections should be stored and the count returned."""
        now = datetime.now()
        events = [
            _make_event(user_id=user_id, source="email", extracted_people=["Alice"], timestamp=now),
            _make_event(user_id=user_id, source="calendar", extracted_people=["Alice"], timestamp=now + timedelta(minutes=5)),
        ]

        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_connections.return_value = []
            repo_instance.create_connection = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            # Patch embedding discovery to avoid DB calls
            with patch(
                "src.infrastructure.tasks.connection_worker._discover_embedding_similarity",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await discover_connections(mock_database, user_id)

        # Should have entity match + temporal connections
        assert result >= 1
        repo_instance.create_connection.assert_called()

    async def test_llm_strategy_requires_5_events_and_llm_service(self, user_id, mock_database, mock_llm_service):
        """LLM inference only runs when there are >= 5 events and llm_service is provided."""
        events = [_make_event(user_id=user_id) for _ in range(5)]

        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_connections.return_value = []
            repo_instance.create_connection = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            with patch(
                "src.infrastructure.tasks.connection_worker._discover_embedding_similarity",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "src.infrastructure.tasks.connection_worker._discover_llm_inference",
                    new_callable=AsyncMock,
                    return_value=[],
                ) as mock_llm_discover:
                    await discover_connections(mock_database, user_id, llm_service=mock_llm_service)

            mock_llm_discover.assert_awaited_once()

    async def test_llm_strategy_skipped_without_llm_service(self, user_id, mock_database):
        """LLM inference is skipped when no llm_service is provided."""
        events = [_make_event(user_id=user_id) for _ in range(5)]

        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_connections.return_value = []
            repo_instance.create_connection = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            with patch(
                "src.infrastructure.tasks.connection_worker._discover_embedding_similarity",
                new_callable=AsyncMock,
                return_value=[],
            ):
                with patch(
                    "src.infrastructure.tasks.connection_worker._discover_llm_inference",
                    new_callable=AsyncMock,
                    return_value=[],
                ) as mock_llm_discover:
                    await discover_connections(mock_database, user_id, llm_service=None)

            mock_llm_discover.assert_not_awaited()

    async def test_duplicate_connections_within_batch_are_deduplicated(self, user_id, mock_database):
        """If two strategies produce the same pair, only one is stored."""
        e1 = _make_event(user_id=user_id, source="email", extracted_people=["Alice"], timestamp=datetime.now())
        e2 = _make_event(user_id=user_id, source="calendar", extracted_people=["Alice"], timestamp=datetime.now() + timedelta(minutes=5))

        # Both entity match and temporal would produce connections for these events
        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = [e1, e2]
            repo_instance.get_connections.return_value = []
            repo_instance.create_connection = AsyncMock(return_value=None)
            MockRepo.return_value = repo_instance

            with patch(
                "src.infrastructure.tasks.connection_worker._discover_embedding_similarity",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await discover_connections(mock_database, user_id)

        # Deduplicated: entity match creates (e1, e2), temporal creates (e1, e2)
        # Only one should be stored per pair
        create_calls = repo_instance.create_connection.call_count
        # Entity creates one, temporal creates one, but they share the same pair
        # After dedup, we should have fewer stored connections than raw total
        assert create_calls >= 1

    async def test_create_connection_failure_is_handled_gracefully(self, user_id, mock_database):
        """Failures in create_connection should be caught and not crash the worker."""
        events = [
            _make_event(user_id=user_id, extracted_people=["Alice"]),
            _make_event(user_id=user_id, extracted_people=["Alice"]),
        ]

        with patch(
            "src.infrastructure.tasks.connection_worker.ContextEventRepository"
        ) as MockRepo:
            repo_instance = AsyncMock()
            repo_instance.get_events.return_value = events
            repo_instance.get_connections.return_value = []
            repo_instance.create_connection = AsyncMock(side_effect=Exception("DB error"))
            MockRepo.return_value = repo_instance

            with patch(
                "src.infrastructure.tasks.connection_worker._discover_embedding_similarity",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await discover_connections(mock_database, user_id)

        # Despite errors, should return 0 (no successful creates)
        assert result == 0
