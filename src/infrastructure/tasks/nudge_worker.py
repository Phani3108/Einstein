"""Nudge worker — periodic task that generates proactive nudges.

Designed to be invoked by arq, celery, or a simple async scheduler.
Each invocation checks for actionable situations and returns a list
of nudge dicts.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.infrastructure.repositories.context_event_repository import ContextEventRepository


async def nudge_task(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate nudges based on upcoming commitments, dormant contacts,
    and imminent meetings.

    Args:
        ctx: Worker context dict.  Expected keys:
            - ``context_repo`` — a ``ContextEventRepository`` instance.
            - ``user_id`` — UUID of the user to check.

    Returns:
        A list of nudge dicts, each with keys:
        ``type``, ``title``, ``body``, ``priority``, ``user_id``, ``related_id``.
    """
    context_repo: ContextEventRepository = ctx["context_repo"]
    user_id = ctx["user_id"]
    now = datetime.utcnow()
    nudges: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. Commitments due within 24 hours
    # ------------------------------------------------------------------
    try:
        commitments = await context_repo.query_events(
            user_id=user_id,
            event_types=["commitment"],
            since=now - timedelta(days=7),
            until=now + timedelta(hours=24),
            limit=20,
        )
        for c in commitments:
            nudges.append(
                {
                    "type": "commitment_due",
                    "title": "Commitment due soon",
                    "body": (c.content or "")[:200],
                    "priority": "high",
                    "user_id": str(user_id),
                    "related_id": str(c.id) if hasattr(c, "id") else None,
                }
            )
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 2. Dormant people approaching 30-day mark
    # ------------------------------------------------------------------
    try:
        # Look for people last contacted 25-35 days ago
        dormant_events = await context_repo.query_events(
            user_id=user_id,
            event_types=["email_received", "email_sent", "meeting_transcript"],
            since=now - timedelta(days=35),
            until=now - timedelta(days=25),
            limit=30,
        )
        seen_people: set = set()
        for ev in dormant_events:
            for person in (ev.extracted_people or []):
                if person not in seen_people:
                    seen_people.add(person)
                    nudges.append(
                        {
                            "type": "dormant_contact",
                            "title": f"Reconnect with {person}",
                            "body": f"You haven't interacted with {person} in about 30 days.",
                            "priority": "medium",
                            "user_id": str(user_id),
                            "related_id": str(ev.id) if hasattr(ev, "id") else None,
                        }
                    )
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 3. Meetings in the next hour with existing context
    # ------------------------------------------------------------------
    try:
        upcoming = await context_repo.query_events(
            user_id=user_id,
            event_types=["calendar_event"],
            since=now,
            until=now + timedelta(hours=1),
            limit=5,
        )
        for ev in upcoming:
            attendees = ev.extracted_people or []
            summary = (ev.content or "Meeting")[:80]
            nudges.append(
                {
                    "type": "meeting_prep",
                    "title": f"Prepare for: {summary}",
                    "body": f"Meeting starting soon with {', '.join(attendees[:3]) or 'attendees'}. Review context now.",
                    "priority": "high",
                    "user_id": str(user_id),
                    "related_id": str(ev.id) if hasattr(ev, "id") else None,
                }
            )
    except Exception:
        pass

    return nudges
