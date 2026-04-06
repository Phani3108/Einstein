"""Pre-meeting briefing worker — generates contextual briefings before meetings.

Designed to be invoked by arq, celery, or a simple async scheduler.
Each invocation finds upcoming meetings and generates rich briefings
with attendee context, open commitments, and suggested talking points.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.infrastructure.repositories.context_event_repository import ContextEventRepository

logger = logging.getLogger(__name__)


async def briefing_task(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate pre-meeting briefings for upcoming meetings.

    Args:
        ctx: Worker context dict.  Expected keys:
            - ``context_repo`` — a ``ContextEventRepository`` instance.
            - ``user_id`` — UUID of the user to check.

    Returns:
        A list of briefing dicts for upcoming meetings.
    """
    context_repo: ContextEventRepository = ctx["context_repo"]
    user_id = ctx["user_id"]

    upcoming = await find_upcoming_meetings(context_repo, user_id, within_minutes=60)
    briefings: List[Dict[str, Any]] = []

    for meeting in upcoming:
        try:
            briefing = await generate_pre_meeting_briefing(
                context_repo, user_id, meeting
            )
            briefings.append(briefing)
        except Exception as exc:
            logger.warning(
                "Failed to generate briefing for meeting %s: %s",
                getattr(meeting, "id", "unknown"),
                exc,
            )

    return briefings


async def find_upcoming_meetings(
    db: ContextEventRepository,
    user_id: UUID,
    within_minutes: int = 60,
) -> list:
    """Find meetings happening within the next N minutes.

    Queries context_events for calendar or meeting events scheduled
    in the near future.

    Args:
        db: The context event repository.
        user_id: User whose calendar to check.
        within_minutes: Look-ahead window in minutes.

    Returns:
        List of upcoming meeting context events.
    """
    now = datetime.utcnow()
    try:
        events = await db.query_events(
            user_id=user_id,
            event_types=["calendar_event", "meeting", "meeting_transcript"],
            since=now,
            until=now + timedelta(minutes=within_minutes),
            limit=10,
        )
        return events or []
    except Exception as exc:
        logger.warning("Failed to query upcoming meetings: %s", exc)
        return []


async def generate_pre_meeting_briefing(
    db: ContextEventRepository,
    user_id: UUID,
    meeting_event: Any,
) -> Dict[str, Any]:
    """Generate a comprehensive pre-meeting briefing.

    For each attendee, gathers recent interactions, open commitments,
    relationship strength indicators, and relevant project context.

    Args:
        db: The context event repository.
        user_id: User requesting the briefing.
        meeting_event: The calendar/meeting context event.

    Returns:
        A briefing dict with attendee details, related projects,
        suggested agenda items, and a context summary.
    """
    now = datetime.utcnow()
    meeting_title = (getattr(meeting_event, "content", None) or "Meeting")[:120]
    meeting_time = (
        getattr(meeting_event, "timestamp", now).isoformat()
        if hasattr(meeting_event, "timestamp")
        else now.isoformat()
    )
    attendees_raw: List[str] = getattr(meeting_event, "extracted_people", None) or []

    # ------------------------------------------------------------------
    # Gather per-attendee intelligence
    # ------------------------------------------------------------------
    attendee_briefings: List[Dict[str, Any]] = []
    all_mentioned_people: set = set(p.lower() for p in attendees_raw)

    for person_name in attendees_raw:
        attendee_info = await _build_attendee_briefing(db, user_id, person_name, now)
        attendee_briefings.append(attendee_info)

    # ------------------------------------------------------------------
    # Gather project context linked to attendees
    # ------------------------------------------------------------------
    related_projects = await _gather_related_projects(db, user_id, attendees_raw)

    # ------------------------------------------------------------------
    # Gather recent context events mentioning any attendee (last 7 days)
    # ------------------------------------------------------------------
    recent_context = await _gather_recent_context(db, user_id, attendees_raw, now)

    # ------------------------------------------------------------------
    # Build suggested agenda from open commitments and recent context
    # ------------------------------------------------------------------
    suggested_agenda = _build_suggested_agenda(attendee_briefings, related_projects)

    # ------------------------------------------------------------------
    # Build narrative context summary
    # ------------------------------------------------------------------
    context_summary = _build_context_summary(
        attendee_briefings, related_projects, recent_context
    )

    return {
        "meeting_title": meeting_title,
        "meeting_time": meeting_time,
        "attendees": attendee_briefings,
        "related_projects": related_projects,
        "suggested_agenda": suggested_agenda,
        "context_summary": context_summary,
        "generated_at": now.isoformat(),
    }


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


async def _build_attendee_briefing(
    db: ContextEventRepository,
    user_id: UUID,
    person_name: str,
    now: datetime,
) -> Dict[str, Any]:
    """Build a detailed briefing block for a single attendee."""

    # Resolve person profile if possible
    role = ""
    organization = ""
    try:
        people = await db.get_people(user_id)
        for p in people:
            if p.name.lower() == person_name.lower():
                role = getattr(p, "role", "") or ""
                organization = getattr(p, "organization", "") or ""
                break
    except Exception:
        pass

    # Last 5 interactions
    recent_interactions: List[Dict[str, str]] = []
    try:
        all_events = await db.query_events(
            user_id=user_id,
            event_types=[
                "email_received", "email_sent", "meeting_transcript",
                "slack_message", "message",
            ],
            since=now - timedelta(days=90),
            until=now,
            limit=200,
        )
        person_events = [
            e for e in all_events
            if person_name.lower() in [
                p.lower() for p in (getattr(e, "extracted_people", None) or [])
            ]
        ]
        # Sort by recency, take last 5
        person_events.sort(
            key=lambda e: getattr(e, "timestamp", now), reverse=True
        )
        for ev in person_events[:5]:
            recent_interactions.append({
                "type": getattr(ev, "event_type", "unknown"),
                "summary": ((getattr(ev, "content", None) or "")[:150]).strip(),
                "date": getattr(ev, "timestamp", now).isoformat(),
            })
    except Exception:
        pass

    # Open commitments involving this person
    open_commitments: List[Dict[str, Any]] = []
    try:
        commitments = await db.query_events(
            user_id=user_id,
            event_types=["commitment"],
            since=now - timedelta(days=30),
            until=now + timedelta(days=30),
            limit=50,
        )
        for c in commitments:
            c_people = [p.lower() for p in (getattr(c, "extracted_people", None) or [])]
            if person_name.lower() in c_people:
                sd = getattr(c, "structured_data", None) or {}
                open_commitments.append({
                    "content": ((getattr(c, "content", None) or "")[:200]).strip(),
                    "due": sd.get("due_date") or sd.get("due") or None,
                    "status": sd.get("status", "open"),
                })
    except Exception:
        pass

    # Relationship strength — interaction counts in 30/60/90-day windows
    count_30d = 0
    count_60d = 0
    count_90d = 0
    last_contact: Optional[str] = None

    try:
        # Reuse person_events gathered above if available
        if not person_events:
            person_events = []
        for ev in person_events:
            ts = getattr(ev, "timestamp", None)
            if not ts:
                continue
            delta = (now - ts).days
            if delta <= 30:
                count_30d += 1
            if delta <= 60:
                count_60d += 1
            if delta <= 90:
                count_90d += 1
        if person_events:
            last_contact = getattr(
                person_events[0], "timestamp", now
            ).isoformat()
    except Exception:
        pass

    relationship_strength = _classify_relationship_strength(count_30d, count_90d)

    # Talking points from recent interactions
    talking_points = _generate_talking_points(
        recent_interactions, open_commitments, person_name
    )

    return {
        "name": person_name,
        "role": role,
        "organization": organization,
        "relationship_strength": relationship_strength,
        "last_contact": last_contact,
        "recent_interactions": recent_interactions,
        "open_commitments": open_commitments,
        "talking_points": talking_points,
    }


def _classify_relationship_strength(
    count_30d: int, count_90d: int
) -> str:
    """Classify relationship strength from interaction counts."""
    if count_30d >= 5:
        return "strong"
    if count_30d >= 2 or count_90d >= 8:
        return "moderate"
    if count_90d >= 2:
        return "weak"
    return "new"


def _generate_talking_points(
    recent_interactions: List[Dict[str, str]],
    open_commitments: List[Dict[str, Any]],
    person_name: str,
) -> List[str]:
    """Generate talking points from recent context."""
    points: List[str] = []

    for commitment in open_commitments[:3]:
        content = commitment.get("content", "")
        if content:
            points.append(f"Follow up on: {content[:80]}")

    for interaction in recent_interactions[:2]:
        summary = interaction.get("summary", "")
        itype = interaction.get("type", "interaction")
        if summary:
            points.append(f"Recent {itype}: {summary[:80]}")

    if not points:
        points.append(f"Reconnect with {person_name} — review shared context")

    return points[:5]


async def _gather_related_projects(
    db: ContextEventRepository,
    user_id: UUID,
    attendees: List[str],
) -> List[Dict[str, str]]:
    """Find projects linked to meeting attendees."""
    projects: List[Dict[str, str]] = []
    try:
        all_projects = await db.get_projects(user_id)
        for proj in (all_projects or []):
            proj_people = [
                p.lower()
                for p in (getattr(proj, "people", None) or getattr(proj, "members", None) or [])
            ]
            attendees_lower = [a.lower() for a in attendees]
            overlap = set(proj_people) & set(attendees_lower)
            if overlap:
                projects.append({
                    "title": getattr(proj, "title", "") or getattr(proj, "name", "") or "",
                    "status": getattr(proj, "status", "active") or "active",
                    "recent_activity": (getattr(proj, "description", "") or "")[:100],
                })
    except Exception:
        pass
    return projects


async def _gather_recent_context(
    db: ContextEventRepository,
    user_id: UUID,
    attendees: List[str],
    now: datetime,
) -> List[Dict[str, str]]:
    """Gather recent context events (last 7 days) mentioning any attendee."""
    context_items: List[Dict[str, str]] = []
    try:
        recent = await db.query_events(
            user_id=user_id,
            event_types=[
                "email_received", "email_sent", "meeting_transcript",
                "slack_message", "message", "note", "thought",
            ],
            since=now - timedelta(days=7),
            until=now,
            limit=100,
        )
        attendees_lower = {a.lower() for a in attendees}
        for ev in (recent or []):
            ev_people = {
                p.lower()
                for p in (getattr(ev, "extracted_people", None) or [])
            }
            if ev_people & attendees_lower:
                context_items.append({
                    "type": getattr(ev, "event_type", ""),
                    "summary": ((getattr(ev, "content", None) or "")[:150]).strip(),
                    "date": getattr(ev, "timestamp", now).isoformat(),
                })
    except Exception:
        pass
    return context_items[:20]


def _build_suggested_agenda(
    attendees: List[Dict[str, Any]],
    projects: List[Dict[str, str]],
) -> List[str]:
    """Infer agenda items from open commitments and project context."""
    agenda: List[str] = []

    for att in attendees:
        for commitment in att.get("open_commitments", [])[:2]:
            content = commitment.get("content", "")
            if content:
                agenda.append(f"Discuss: {content[:80]}")

    for proj in projects[:3]:
        title = proj.get("title", "")
        if title:
            agenda.append(f"Project update: {title}")

    if not agenda:
        agenda.append("General catch-up and alignment")

    return agenda[:7]


def _build_context_summary(
    attendees: List[Dict[str, Any]],
    projects: List[Dict[str, str]],
    recent_context: List[Dict[str, str]],
) -> str:
    """Build a brief narrative summary of recent relevant context."""
    parts: List[str] = []

    attendee_names = [a["name"] for a in attendees]
    if attendee_names:
        parts.append(f"Meeting with {', '.join(attendee_names[:5])}.")

    total_commitments = sum(
        len(a.get("open_commitments", [])) for a in attendees
    )
    if total_commitments:
        parts.append(f"{total_commitments} open commitment(s) involving attendees.")

    if projects:
        proj_names = [p["title"] for p in projects[:3] if p.get("title")]
        if proj_names:
            parts.append(f"Related projects: {', '.join(proj_names)}.")

    if recent_context:
        parts.append(
            f"{len(recent_context)} relevant context event(s) in the last 7 days."
        )

    return " ".join(parts) if parts else "No recent context available for this meeting."
