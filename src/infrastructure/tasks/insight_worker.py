"""Insight worker: Temporal memory, dormancy detection, and resurfacing.

Responsibilities:
  - Compute freshness scores for people and projects (exponential decay)
  - Detect dormancy (projects 14+ days, people 21+ days)
  - Generate morning briefings and weekly digests
  - Track overdue commitments

Runs as a daily cron job.
"""

import logging
import math
import uuid as uuid_mod
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update, and_, desc, func

from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    ContextEventModel,
    PersonProfileModel,
    ProjectModel,
    CommitmentModel,
    ResurfacingLogModel,
)
from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

# Freshness decay constant (half-life ~ 14 days)
DECAY_RATE = 0.05
# Dormancy thresholds
PROJECT_DORMANCY_DAYS = 14
PERSON_DORMANCY_DAYS = 21
# Commitment overdue grace period
COMMITMENT_GRACE_HOURS = 24


def compute_freshness(days_since_last: float, link_boost: float = 0.0) -> float:
    """Compute freshness score using exponential decay.

    freshness = exp(-DECAY_RATE * days) + link_boost
    Clamped to [0, 1].
    """
    base = math.exp(-DECAY_RATE * max(0, days_since_last))
    return min(1.0, max(0.0, base + link_boost))


async def update_freshness_scores(database: Database, user_id: UUID) -> dict:
    """Recompute freshness scores and dormancy for all people and projects.

    Returns:
        Dict with counts: {"people_updated", "projects_updated", "dormant_people", "dormant_projects"}
    """
    now = datetime.now()
    stats = {"people_updated": 0, "projects_updated": 0, "dormant_people": 0, "dormant_projects": 0}

    async with database.session() as session:
        # --- People freshness ---
        people_result = await session.execute(
            select(PersonProfileModel).where(PersonProfileModel.user_id == user_id)
        )
        people = people_result.scalars().all()

        for person in people:
            last_active = person.last_activity_at or person.last_seen or person.created_at
            days_since = (now - last_active).total_seconds() / 86400 if last_active else 999

            # Count recent connections as link boost
            conn_count = await _count_person_connections(session, user_id, person.name, days=30)
            link_boost = min(0.2, conn_count * 0.02)

            freshness = compute_freshness(days_since, link_boost)
            dormancy = int(days_since) if days_since > PERSON_DORMANCY_DAYS else 0

            person.freshness_score = round(freshness, 4)
            person.dormancy_days = dormancy

            if dormancy > 0:
                stats["dormant_people"] += 1
            stats["people_updated"] += 1

        # --- Projects freshness ---
        projects_result = await session.execute(
            select(ProjectModel).where(
                and_(ProjectModel.user_id == user_id, ProjectModel.status == "active")
            )
        )
        projects = projects_result.scalars().all()

        for project in projects:
            last_active = project.last_activity_at or project.updated_at or project.created_at
            days_since = (now - last_active).total_seconds() / 86400 if last_active else 999

            dormancy = int(days_since) if days_since > PROJECT_DORMANCY_DAYS else 0
            project.dormancy_days = dormancy

            if dormancy > 0:
                stats["dormant_projects"] += 1
            stats["projects_updated"] += 1

        await session.commit()

    logger.info(
        "Freshness update for user %s: %d people, %d projects, %d dormant people, %d dormant projects",
        user_id,
        stats["people_updated"],
        stats["projects_updated"],
        stats["dormant_people"],
        stats["dormant_projects"],
    )
    return stats


async def _count_person_connections(session, user_id: UUID, person_name: str, days: int) -> int:
    """Count how many recent events mention a person (used for link boost)."""
    since = datetime.now() - timedelta(days=days)
    stmt = (
        select(func.count())
        .select_from(ContextEventModel)
        .where(
            and_(
                ContextEventModel.user_id == user_id,
                ContextEventModel.timestamp >= since,
                ContextEventModel.extracted_people.any(person_name),
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar() or 0


async def check_overdue_commitments(database: Database, user_id: UUID) -> List[dict]:
    """Find and flag overdue commitments.

    Returns list of overdue commitment summaries.
    """
    now = datetime.now()
    overdue = []

    async with database.session() as session:
        stmt = (
            select(CommitmentModel)
            .where(
                and_(
                    CommitmentModel.user_id == user_id,
                    CommitmentModel.status == "open",
                    CommitmentModel.due_date.isnot(None),
                    CommitmentModel.due_date < now - timedelta(hours=COMMITMENT_GRACE_HOURS),
                )
            )
            .order_by(CommitmentModel.due_date)
        )
        result = await session.execute(stmt)
        for commitment in result.scalars().all():
            commitment.status = "overdue"
            overdue.append({
                "id": str(commitment.id),
                "description": commitment.description,
                "due_date": commitment.due_date.isoformat() if commitment.due_date else None,
                "days_overdue": (now - commitment.due_date).days if commitment.due_date else 0,
            })

        await session.commit()

    if overdue:
        logger.info("Found %d overdue commitments for user %s", len(overdue), user_id)
    return overdue


async def generate_morning_briefing(
    database: Database,
    llm_service: LLMService,
    user_id: UUID,
) -> dict:
    """Generate a morning briefing with actionable intelligence.

    Combines:
    - Overdue commitments
    - Dormant projects needing attention
    - People to follow up with
    - Today's calendar events
    - Recent patterns

    Returns briefing payload dict.
    """
    repo = ContextEventRepository(database)

    # Gather data
    overdue = await check_overdue_commitments(database, user_id)
    freshness = await update_freshness_scores(database, user_id)

    # Get today's events
    today_start = datetime.now().replace(hour=0, minute=0, second=0)
    today_events = await repo.get_events(
        user_id=user_id, since=today_start, limit=50
    )

    # Get dormant entities
    async with database.session() as session:
        dormant_people = await session.execute(
            select(PersonProfileModel)
            .where(
                and_(
                    PersonProfileModel.user_id == user_id,
                    PersonProfileModel.dormancy_days > 0,
                )
            )
            .order_by(desc(PersonProfileModel.dormancy_days))
            .limit(5)
        )
        stale_people = [
            {"name": p.name, "dormancy_days": p.dormancy_days, "last_seen": p.last_seen.isoformat() if p.last_seen else None}
            for p in dormant_people.scalars().all()
        ]

        dormant_projects = await session.execute(
            select(ProjectModel)
            .where(
                and_(
                    ProjectModel.user_id == user_id,
                    ProjectModel.dormancy_days > 0,
                    ProjectModel.status == "active",
                )
            )
            .order_by(desc(ProjectModel.dormancy_days))
            .limit(5)
        )
        stale_projects = [
            {"title": p.title, "dormancy_days": p.dormancy_days}
            for p in dormant_projects.scalars().all()
        ]

    # Build briefing
    briefing = {
        "date": datetime.now().isoformat()[:10],
        "overdue_commitments": overdue[:5],
        "stale_people": stale_people,
        "stale_projects": stale_projects,
        "today_event_count": len(today_events),
        "attention_items": [],
    }

    # Attention items
    if overdue:
        briefing["attention_items"].append(
            f"{len(overdue)} overdue commitment(s)"
        )
    if stale_people:
        briefing["attention_items"].append(
            f"Follow up with: {', '.join(p['name'] for p in stale_people[:3])}"
        )
    if stale_projects:
        briefing["attention_items"].append(
            f"Stale projects: {', '.join(p['title'] for p in stale_projects[:3])}"
        )

    # Generate LLM summary if there's enough data
    if today_events or overdue or stale_people:
        try:
            context = f"""Morning briefing data:
- Date: {briefing['date']}
- Overdue commitments: {len(overdue)}
- Stale people to follow up: {', '.join(p['name'] for p in stale_people)}
- Stale projects: {', '.join(p['title'] for p in stale_projects)}
- Today's events so far: {len(today_events)}"""

            summary = await llm_service.generate(
                context,
                system_prompt="You are Einstein. Write a 2-3 sentence morning briefing summary. Be concise, actionable, warm. No JSON.",
            )
            briefing["summary"] = summary.strip()
        except Exception:
            briefing["summary"] = f"You have {len(briefing['attention_items'])} items needing attention today."

    # Log the resurfacing
    await _log_resurfacing(database, user_id, "morning_briefing", briefing)

    return briefing


async def generate_weekly_digest(
    database: Database,
    llm_service: LLMService,
    user_id: UUID,
) -> dict:
    """Generate a weekly digest of activity, themes, and attention items."""
    repo = ContextEventRepository(database)
    since = datetime.now() - timedelta(days=7)

    events = await repo.get_events(user_id=user_id, since=since, limit=200)
    people = await repo.get_people(user_id, limit=50)
    connections = await repo.get_connections(user_id=user_id, limit=200)

    # Aggregate topics
    topic_counts: dict[str, int] = {}
    for e in events:
        for t in (e.topics or []):
            topic_counts[t] = topic_counts.get(t, 0) + 1
    top_topics = sorted(topic_counts.items(), key=lambda x: -x[1])[:10]

    # Source breakdown
    source_counts: dict[str, int] = {}
    for e in events:
        source_counts[e.source] = source_counts.get(e.source, 0) + 1

    # Active people
    active_people = [p for p in people if p.last_seen and (datetime.now() - p.last_seen).days <= 7]

    digest = {
        "period": f"{since.isoformat()[:10]} to {datetime.now().isoformat()[:10]}",
        "total_events": len(events),
        "sources": dict(source_counts),
        "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
        "new_connections": len([c for c in connections if c.discovered_at >= since]),
        "active_people": [p.name for p in active_people[:10]],
        "people_count": len(active_people),
    }

    # LLM summary
    try:
        context = f"""Weekly digest data:
- Period: {digest['period']}
- Total events: {digest['total_events']}
- Sources: {digest['sources']}
- Top topics: {', '.join(t for t, _ in top_topics[:5])}
- Active people: {', '.join(digest['active_people'][:5])}
- New connections: {digest['new_connections']}"""

        summary = await llm_service.generate(
            context,
            system_prompt="You are Einstein. Write a 3-4 sentence weekly digest summary. Highlight patterns and themes. Be insightful, not just factual. No JSON.",
        )
        digest["summary"] = summary.strip()
    except Exception:
        digest["summary"] = f"This week: {digest['total_events']} events across {len(source_counts)} sources."

    await _log_resurfacing(database, user_id, "weekly_digest", digest)
    return digest


async def _log_resurfacing(
    database: Database,
    user_id: UUID,
    resurface_type: str,
    payload: dict,
) -> None:
    """Log a resurfacing event."""
    async with database.session() as session:
        log = ResurfacingLogModel(
            id=uuid_mod.uuid4(),
            user_id=user_id,
            type=resurface_type,
            payload=payload,
        )
        session.add(log)
        await session.commit()


async def insight_task(ctx: dict) -> dict:
    """arq task entry point for daily insight generation."""
    database = ctx["database"]
    llm_service = ctx["llm_service"]
    from src.infrastructure.tasks.tier1_worker import _get_active_user_ids

    user_ids = await _get_active_user_ids(database)
    results = {}
    for uid in user_ids:
        freshness = await update_freshness_scores(database, uid)
        overdue = await check_overdue_commitments(database, uid)
        briefing = await generate_morning_briefing(database, llm_service, uid)
        results[str(uid)] = {
            "freshness": freshness,
            "overdue_commitments": len(overdue),
            "briefing_generated": bool(briefing),
        }
    return results
