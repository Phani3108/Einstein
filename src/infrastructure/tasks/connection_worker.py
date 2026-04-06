"""Connection discovery worker: Find and create links between context events.

Five discovery strategies:
  1. Entity match — same person mentioned in two events
  2. Temporal cluster — events within 30 min from different sources
  3. Embedding similarity — cosine similarity above threshold
  4. LLM inference — batch clusters through LLM for deeper connections
  5. Causal chains — meeting → follow-up email → task creation

Runs every ~5 minutes.
"""

import logging
import math
import uuid as uuid_mod
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple
from uuid import UUID

from src.domain.entities.context_event import Connection, ContextEvent
from src.infrastructure.database.connection import Database
from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

# Thresholds
TEMPORAL_WINDOW_MINUTES = 30
SIMILARITY_THRESHOLD = 0.75
MAX_CONNECTIONS_PER_EVENT = 5


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def discover_connections(
    database: Database,
    user_id: UUID,
    llm_service: Optional[LLMService] = None,
    lookback_hours: int = 24,
) -> int:
    """Run all connection discovery strategies for a user.

    Args:
        database: Database connection
        user_id: User to process
        llm_service: Optional LLM service for inference-based connections
        lookback_hours: How far back to look for new events

    Returns:
        Number of new connections created
    """
    repo = ContextEventRepository(database)
    since = datetime.now() - timedelta(hours=lookback_hours)
    recent_events = await repo.get_events(user_id=user_id, since=since, limit=200)

    if len(recent_events) < 2:
        return 0

    # Get existing connections to avoid duplicates
    existing = await repo.get_connections(user_id=user_id, limit=1000)
    existing_pairs: Set[Tuple[UUID, UUID]] = set()
    for c in existing:
        existing_pairs.add((c.source_event_id, c.target_event_id))
        existing_pairs.add((c.target_event_id, c.source_event_id))

    new_connections: List[Connection] = []

    # Strategy 1: Entity match (same person in two events)
    entity_conns = _discover_entity_matches(recent_events, existing_pairs)
    new_connections.extend(entity_conns)

    # Strategy 2: Temporal cluster (events within 30 min from different sources)
    temporal_conns = _discover_temporal_clusters(recent_events, existing_pairs)
    new_connections.extend(temporal_conns)

    # Strategy 3: Embedding similarity (if embeddings available)
    embedding_conns = await _discover_embedding_similarity(
        database, recent_events, existing_pairs
    )
    new_connections.extend(embedding_conns)

    # Strategy 4: LLM inference (optional, for batched clusters)
    if llm_service and len(recent_events) >= 5:
        llm_conns = await _discover_llm_inference(
            llm_service, recent_events, existing_pairs, user_id
        )
        new_connections.extend(llm_conns)

    # Strategy 5: Causal chains (meeting → email → task)
    causal_conns = _discover_causal_chains(recent_events, existing_pairs)
    new_connections.extend(causal_conns)

    # Deduplicate within batch
    seen: Set[Tuple[UUID, UUID]] = set()
    unique_conns = []
    for conn in new_connections:
        pair = (conn.source_event_id, conn.target_event_id)
        reverse = (conn.target_event_id, conn.source_event_id)
        if pair not in seen and reverse not in seen:
            seen.add(pair)
            unique_conns.append(conn)

    # Store new connections
    created = 0
    for conn in unique_conns:
        try:
            await repo.create_connection(conn)
            created += 1
        except Exception as e:
            logger.warning("Failed to create connection: %s", e)

    llm_count = len(new_connections) - len(entity_conns) - len(temporal_conns) - len(embedding_conns) - len(causal_conns)
    logger.info(
        "Connection discovery: %d new connections for user %s "
        "(entity=%d, temporal=%d, embedding=%d, llm=%d, causal=%d)",
        created,
        user_id,
        len(entity_conns),
        len(temporal_conns),
        len(embedding_conns),
        llm_count,
        len(causal_conns),
    )
    return created


def _discover_entity_matches(
    events: List[ContextEvent],
    existing: Set[Tuple[UUID, UUID]],
) -> List[Connection]:
    """Find events that mention the same person."""
    # Build person → events index
    person_events: dict[str, list[ContextEvent]] = defaultdict(list)
    for event in events:
        for person in event.extracted_people:
            person_events[person.lower()].append(event)

    connections = []
    for person, evts in person_events.items():
        if len(evts) < 2:
            continue
        # Connect pairs (limited to avoid explosion)
        for i in range(min(len(evts), 5)):
            for j in range(i + 1, min(len(evts), 5)):
                pair = (evts[i].id, evts[j].id)
                if pair in existing or (pair[1], pair[0]) in existing:
                    continue
                connections.append(
                    Connection(
                        id=uuid_mod.uuid4(),
                        user_id=evts[i].user_id,
                        source_event_id=evts[i].id,
                        target_event_id=evts[j].id,
                        connection_type="same_person",
                        strength=0.8,
                        evidence=f"Both mention: {person}",
                        method="entity_match",
                    )
                )
    return connections


def _discover_temporal_clusters(
    events: List[ContextEvent],
    existing: Set[Tuple[UUID, UUID]],
) -> List[Connection]:
    """Find events within 30 minutes from different sources."""
    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    connections = []

    for i, event_a in enumerate(sorted_events):
        for j in range(i + 1, len(sorted_events)):
            event_b = sorted_events[j]
            delta = abs((event_b.timestamp - event_a.timestamp).total_seconds())

            if delta > TEMPORAL_WINDOW_MINUTES * 60:
                break  # sorted, so all subsequent are further away

            # Only connect events from different sources
            if event_a.source == event_b.source:
                continue

            pair = (event_a.id, event_b.id)
            if pair in existing or (pair[1], pair[0]) in existing:
                continue

            # Strength inversely proportional to time gap
            strength = max(0.3, 1.0 - (delta / (TEMPORAL_WINDOW_MINUTES * 60)))

            connections.append(
                Connection(
                    id=uuid_mod.uuid4(),
                    user_id=event_a.user_id,
                    source_event_id=event_a.id,
                    target_event_id=event_b.id,
                    connection_type="temporal",
                    strength=round(strength, 2),
                    evidence=f"Within {int(delta/60)} min ({event_a.source} ↔ {event_b.source})",
                    method="temporal_cluster",
                )
            )

    return connections[:50]  # cap to avoid explosion


async def _discover_embedding_similarity(
    database: Database,
    events: List[ContextEvent],
    existing: Set[Tuple[UUID, UUID]],
) -> List[Connection]:
    """Find semantically similar events using embedding cosine similarity."""
    from sqlalchemy import select
    from src.infrastructure.database.models import ContextEventModel

    # Load embeddings for recent events
    event_embeddings: dict[UUID, List[float]] = {}
    async with database.session() as session:
        stmt = (
            select(ContextEventModel.id, ContextEventModel.embedding)
            .where(ContextEventModel.id.in_([e.id for e in events]))
            .where(ContextEventModel.embedding.isnot(None))
        )
        result = await session.execute(stmt)
        for row in result.all():
            if row[1]:  # has embedding
                event_embeddings[row[0]] = row[1]

    if len(event_embeddings) < 2:
        return []

    connections = []
    event_ids = list(event_embeddings.keys())
    event_map = {e.id: e for e in events}

    for i in range(len(event_ids)):
        for j in range(i + 1, len(event_ids)):
            eid_a, eid_b = event_ids[i], event_ids[j]
            pair = (eid_a, eid_b)
            if pair in existing or (pair[1], pair[0]) in existing:
                continue

            sim = cosine_similarity(event_embeddings[eid_a], event_embeddings[eid_b])
            if sim >= SIMILARITY_THRESHOLD:
                event_a = event_map.get(eid_a)
                if not event_a:
                    continue
                connections.append(
                    Connection(
                        id=uuid_mod.uuid4(),
                        user_id=event_a.user_id,
                        source_event_id=eid_a,
                        target_event_id=eid_b,
                        connection_type="semantic_similar",
                        strength=round(sim, 3),
                        evidence=f"Cosine similarity: {sim:.3f}",
                        method="embedding_similarity",
                    )
                )

    # Keep top N by strength
    connections.sort(key=lambda c: c.strength, reverse=True)
    return connections[:30]


LLM_CONNECTION_SYSTEM = """You are Einstein, a personal context intelligence engine.
Analyze these context events and identify meaningful connections between them.

Return ONLY valid JSON:
{
  "connections": [
    {
      "event_a_index": 0,
      "event_b_index": 1,
      "type": "follow_up|same_topic|causal|related",
      "strength": 0.8,
      "evidence": "Why these events are connected"
    }
  ]
}

Only include genuine, non-obvious connections. If no meaningful connections exist, return {"connections": []}."""


async def _discover_llm_inference(
    llm_service: LLMService,
    events: List[ContextEvent],
    existing: Set[Tuple[UUID, UUID]],
    user_id: UUID,
) -> List[Connection]:
    """Use LLM to discover deeper connections between event clusters."""
    import json

    # Take a sample of recent events (avoid sending too many)
    sample = events[:10]
    events_text = "\n".join(
        f"[{i}] [{e.source}/{e.event_type}] {e.timestamp.isoformat()[:16]}: "
        f"{(e.content or '')[:200]}"
        for i, e in enumerate(sample)
    )

    prompt = f"Find connections between these {len(sample)} context events:\n\n{events_text}"

    try:
        raw = await llm_service.generate(prompt, system_prompt=LLM_CONNECTION_SYSTEM)
        data = json.loads(raw)
        llm_connections = data.get("connections", [])
    except Exception as e:
        logger.warning("LLM connection inference failed: %s", e)
        return []

    connections = []
    for lc in llm_connections:
        idx_a = lc.get("event_a_index", -1)
        idx_b = lc.get("event_b_index", -1)
        if idx_a < 0 or idx_b < 0 or idx_a >= len(sample) or idx_b >= len(sample):
            continue

        event_a = sample[idx_a]
        event_b = sample[idx_b]
        pair = (event_a.id, event_b.id)
        if pair in existing or (pair[1], pair[0]) in existing:
            continue

        connections.append(
            Connection(
                id=uuid_mod.uuid4(),
                user_id=user_id,
                source_event_id=event_a.id,
                target_event_id=event_b.id,
                connection_type=lc.get("type", "related"),
                strength=min(1.0, max(0.1, lc.get("strength", 0.5))),
                evidence=lc.get("evidence", "LLM-inferred connection"),
                method="llm_inference",
            )
        )

    return connections


def _discover_causal_chains(
    events: List[ContextEvent],
    existing: Set[Tuple[UUID, UUID]],
) -> List[Connection]:
    """Detect causal chains: meeting -> follow-up email -> task creation."""
    connections = []

    # Sort by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)

    # Build source index for quick lookup
    by_source: dict[str, list[ContextEvent]] = defaultdict(list)
    for e in sorted_events:
        by_source[e.source].append(e)

    # Rule 1: Calendar event ends -> email sent to same attendees within 2 hours
    calendar_events = [e for e in sorted_events if e.source == "calendar" or e.event_type == "meeting_transcript"]
    email_events = [e for e in sorted_events if e.source == "gmail" or e.source == "outlook"]

    for cal_event in calendar_events:
        cal_people = set(p.lower() for p in cal_event.extracted_people)
        if not cal_people:
            continue

        for email_event in email_events:
            # Email must be within 2 hours after the calendar event
            delta = (email_event.timestamp - cal_event.timestamp).total_seconds()
            if delta < 0 or delta > 7200:  # 0 to 2 hours
                continue

            email_people = set(p.lower() for p in email_event.extracted_people)
            overlap = cal_people & email_people
            if not overlap:
                continue

            pair = (cal_event.id, email_event.id)
            if pair in existing or (pair[1], pair[0]) in existing:
                continue

            connections.append(Connection(
                id=uuid_mod.uuid4(),
                user_id=cal_event.user_id,
                source_event_id=cal_event.id,
                target_event_id=email_event.id,
                connection_type="follow_up",
                strength=0.85,
                evidence=f"Email to {', '.join(overlap)} within {int(delta/60)}m of meeting",
                method="causal_chain",
            ))

    # Rule 2: Email/message contains reference to a Jira/Linear issue
    jira_events = [e for e in sorted_events if e.source in ("jira", "linear", "github")]
    message_events = [e for e in sorted_events if e.source in ("gmail", "outlook", "slack", "whatsapp")]

    for msg_event in message_events:
        content = (msg_event.content or "").lower()
        for task_event in jira_events:
            sd = task_event.structured_data or {}
            issue_key = sd.get("issue_key", "").lower()
            issue_url = sd.get("url", "").lower()

            if not issue_key and not issue_url:
                continue

            if (issue_key and issue_key in content) or (issue_url and issue_url in content):
                pair = (msg_event.id, task_event.id)
                if pair in existing or (pair[1], pair[0]) in existing:
                    continue

                connections.append(Connection(
                    id=uuid_mod.uuid4(),
                    user_id=msg_event.user_id,
                    source_event_id=msg_event.id,
                    target_event_id=task_event.id,
                    connection_type="reference",
                    strength=0.9,
                    evidence=f"Message references {issue_key or 'issue'}",
                    method="causal_chain",
                ))

    # Rule 3: Commitment from meeting -> Jira ticket created within 48 hours
    for cal_event in calendar_events:
        cal_actions = (cal_event.structured_data or {}).get("action_items", [])
        if not cal_actions:
            continue

        for task_event in jira_events:
            delta = (task_event.timestamp - cal_event.timestamp).total_seconds()
            if delta < 0 or delta > 172800:  # 0 to 48 hours
                continue

            task_title = (task_event.structured_data or {}).get("title", "").lower()
            task_content = (task_event.content or "").lower()

            # Check if any action item text appears in the task
            for action in cal_actions[:5]:
                action_text = str(action).lower()
                keywords = [w for w in action_text.split() if len(w) > 4]
                matches = sum(1 for kw in keywords if kw in task_title or kw in task_content)
                if matches >= 2:
                    pair = (cal_event.id, task_event.id)
                    if pair in existing or (pair[1], pair[0]) in existing:
                        continue

                    connections.append(Connection(
                        id=uuid_mod.uuid4(),
                        user_id=cal_event.user_id,
                        source_event_id=cal_event.id,
                        target_event_id=task_event.id,
                        connection_type="fulfillment",
                        strength=0.75,
                        evidence=f"Task may fulfill action item from meeting",
                        method="causal_chain",
                    ))
                    break

    return connections[:30]


async def connection_task(ctx: dict) -> int:
    """arq task entry point for connection discovery."""
    database = ctx["database"]
    llm_service = ctx.get("llm_service")
    from src.infrastructure.tasks.tier1_worker import _get_active_user_ids

    user_ids = await _get_active_user_ids(database)
    total = 0
    for uid in user_ids:
        total += await discover_connections(database, uid, llm_service)
    return total
