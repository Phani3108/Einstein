"""Project inference worker: Auto-link context events to projects.

Builds a topic/entity fingerprint per project from past linked events,
then matches new events against project fingerprints.
"""

import logging
import re
import uuid as uuid_mod
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from sqlalchemy import text

from src.infrastructure.database.connection import Database

logger = logging.getLogger(__name__)

# Scoring weights
TOPIC_WEIGHT = 0.4
PEOPLE_WEIGHT = 0.35
KEYWORD_WEIGHT = 0.25

# Minimum score to create a link
LINK_THRESHOLD = 0.5

# Stop words to exclude from keyword matching
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "ought",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than",
    "too", "very", "just", "about", "above", "after", "again", "also",
    "before", "below", "between", "from", "further", "here", "how",
    "into", "its", "itself", "now", "once", "out", "over", "then",
    "there", "these", "this", "that", "those", "through", "under",
    "until", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "for", "of", "on", "in", "to", "at", "by", "up",
})


def _extract_keywords(text_content: str) -> Set[str]:
    """Extract meaningful keywords from text, excluding stop words."""
    if not text_content:
        return set()
    words = re.findall(r"[a-zA-Z]{3,}", text_content.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 3}


def _compute_overlap_score(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard-like overlap between two sets, normalized to [0, 1]."""
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    # Use the smaller set as denominator to favour recall
    denominator = min(len(set_a), len(set_b))
    return len(intersection) / denominator if denominator > 0 else 0.0


async def _load_active_projects(session, user_id: UUID) -> List[dict]:
    """Load all active projects for a user."""
    result = await session.execute(
        text(
            "SELECT id, title, description, last_activity_at "
            "FROM projects "
            "WHERE user_id = :uid AND status = 'active' "
            "ORDER BY last_activity_at DESC NULLS LAST"
        ),
        {"uid": str(user_id)},
    )
    rows = result.fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2] or "",
            "last_activity_at": row[3],
        }
        for row in rows
    ]


async def _build_project_fingerprint(
    session, project: dict
) -> dict:
    """Build a topic/people/keyword fingerprint for a project.

    Uses events already linked to this project. Falls back to
    project title + description if no events are linked yet.
    """
    project_id = project["id"]

    # Get events linked to this project
    result = await session.execute(
        text(
            "SELECT ce.topics, ce.extracted_people, ce.content "
            "FROM context_events ce "
            "INNER JOIN project_event_links pel ON pel.event_id = ce.id "
            "WHERE pel.project_id = :pid "
            "ORDER BY ce.timestamp DESC "
            "LIMIT 100"
        ),
        {"pid": str(project_id)},
    )
    rows = result.fetchall()

    topics: Set[str] = set()
    people: Set[str] = set()
    keywords: Set[str] = set()

    if rows:
        for row in rows:
            row_topics = row[0] or []
            row_people = row[1] or []
            row_content = row[2] or ""
            topics.update(t.lower() for t in row_topics)
            people.update(p.lower() for p in row_people)
            keywords.update(_extract_keywords(row_content))
    else:
        # Fallback: use project title and description as fingerprint
        title_desc = f"{project['title']} {project['description']}"
        keywords = _extract_keywords(title_desc)
        # Use title words as pseudo-topics
        topics = {w.lower() for w in project["title"].split() if len(w) > 3}

    return {
        "topics": topics,
        "people": people,
        "keywords": keywords,
    }


async def _get_unlinked_events(
    session, user_id: UUID, since: datetime, limit: int = 200
) -> List[dict]:
    """Get recent events that are not yet linked to any project."""
    result = await session.execute(
        text(
            "SELECT ce.id, ce.topics, ce.extracted_people, ce.content, ce.timestamp "
            "FROM context_events ce "
            "WHERE ce.user_id = :uid "
            "  AND ce.timestamp >= :since "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM project_event_links pel WHERE pel.event_id = ce.id"
            "  ) "
            "ORDER BY ce.timestamp DESC "
            "LIMIT :lim"
        ),
        {"uid": str(user_id), "since": since, "lim": limit},
    )
    rows = result.fetchall()
    return [
        {
            "id": row[0],
            "topics": row[1] or [],
            "extracted_people": row[2] or [],
            "content": row[3] or "",
            "timestamp": row[4],
        }
        for row in rows
    ]


def _score_event_against_project(
    event: dict, fingerprint: dict
) -> float:
    """Score how well an event matches a project fingerprint."""
    event_topics = {t.lower() for t in event["topics"]}
    event_people = {p.lower() for p in event["extracted_people"]}
    event_keywords = _extract_keywords(event["content"])

    topic_score = _compute_overlap_score(event_topics, fingerprint["topics"])
    people_score = _compute_overlap_score(event_people, fingerprint["people"])
    keyword_score = _compute_overlap_score(event_keywords, fingerprint["keywords"])

    return (
        topic_score * TOPIC_WEIGHT
        + people_score * PEOPLE_WEIGHT
        + keyword_score * KEYWORD_WEIGHT
    )


async def infer_project_links(
    database: Database,
    user_id: UUID,
    lookback_hours: int = 24,
) -> int:
    """Run project inference for a user: match unlinked events to projects.

    Args:
        database: Database connection
        user_id: User to process
        lookback_hours: How far back to look for new events

    Returns:
        Number of new project-event links created
    """
    since = datetime.now() - timedelta(hours=lookback_hours)
    created = 0
    projects_updated: Set[UUID] = set()

    async with database.session() as session:
        # 1. Load active projects
        projects = await _load_active_projects(session, user_id)
        if not projects:
            return 0

        # 2. Build fingerprints for each project
        fingerprints: Dict[UUID, dict] = {}
        for project in projects:
            fingerprints[project["id"]] = await _build_project_fingerprint(
                session, project
            )

        # 3. Get unlinked recent events
        unlinked_events = await _get_unlinked_events(session, user_id, since)
        if not unlinked_events:
            return 0

        # 4. Score each event against each project
        for event in unlinked_events:
            best_project_id = None
            best_score = 0.0

            for project in projects:
                pid = project["id"]
                fp = fingerprints[pid]

                # Skip projects with empty fingerprints
                if not fp["topics"] and not fp["people"] and not fp["keywords"]:
                    continue

                score = _score_event_against_project(event, fp)
                if score > best_score:
                    best_score = score
                    best_project_id = pid

            if best_project_id and best_score >= LINK_THRESHOLD:
                try:
                    await session.execute(
                        text(
                            "INSERT INTO project_event_links (project_id, event_id, confidence, method) "
                            "VALUES (:pid, :eid, :conf, 'auto') "
                            "ON CONFLICT (project_id, event_id) DO NOTHING"
                        ),
                        {
                            "pid": str(best_project_id),
                            "eid": str(event["id"]),
                            "conf": round(best_score, 3),
                        },
                    )
                    created += 1
                    projects_updated.add(best_project_id)
                except Exception as e:
                    logger.warning("Failed to create project-event link: %s", e)

        # 5. Update last_activity_at for projects that got new links
        for pid in projects_updated:
            try:
                await session.execute(
                    text(
                        "UPDATE projects SET last_activity_at = :now "
                        "WHERE id = :pid"
                    ),
                    {"now": datetime.now(), "pid": str(pid)},
                )
            except Exception as e:
                logger.warning("Failed to update project last_activity_at: %s", e)

        await session.commit()

    logger.info(
        "Project inference: %d new links for user %s across %d projects",
        created,
        user_id,
        len(projects_updated),
    )
    return created


async def project_inference_task(ctx: dict) -> int:
    """arq task entry point for project inference."""
    database = ctx["database"]
    from src.infrastructure.tasks.tier1_worker import _get_active_user_ids

    user_ids = await _get_active_user_ids(database)
    total = 0
    for uid in user_ids:
        total += await infer_project_links(database, uid)
    return total
