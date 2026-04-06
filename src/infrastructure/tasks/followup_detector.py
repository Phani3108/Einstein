"""Smart follow-up detector — identifies pending follow-ups and stale threads.

Designed to be invoked by arq, celery, or a simple async scheduler.
Detects unanswered emails, meetings without follow-up, stale
conversations, and commitments due soon without recent activity.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from src.infrastructure.repositories.context_event_repository import ContextEventRepository

logger = logging.getLogger(__name__)


async def followup_detection_task(ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect pending follow-ups for a user.

    Args:
        ctx: Worker context dict.  Expected keys:
            - ``context_repo`` — a ``ContextEventRepository`` instance.
            - ``user_id`` — UUID of the user.

    Returns:
        A list of follow-up suggestion dicts.
    """
    context_repo: ContextEventRepository = ctx["context_repo"]
    user_id = ctx["user_id"]

    try:
        return await detect_pending_followups(context_repo, user_id)
    except Exception as exc:
        logger.error("Follow-up detection failed for %s: %s", user_id, exc)
        return []


async def detect_pending_followups(
    db: ContextEventRepository,
    user_id: UUID,
) -> List[Dict[str, Any]]:
    """Detect all categories of pending follow-ups.

    Categories:
        1. Unanswered emails (received 48h+ ago, no reply)
        2. Meetings without follow-up (ended 24h+ ago, commitments made, no outbound)
        3. Stale conversations (last inbound message 3+ days ago)
        4. Commitment reminders (due within 48h, no related activity)

    Args:
        db: The context event repository.
        user_id: User to check.

    Returns:
        A list of follow-up suggestion dicts sorted by priority.
    """
    now = datetime.utcnow()
    followups: List[Dict[str, Any]] = []

    # Run all detectors
    followups.extend(await _detect_unanswered_emails(db, user_id, now))
    followups.extend(await _detect_meeting_followups(db, user_id, now))
    followups.extend(await _detect_stale_conversations(db, user_id, now))
    followups.extend(await _detect_commitment_reminders(db, user_id, now))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    followups.sort(key=lambda f: priority_order.get(f.get("priority", "low"), 3))

    return followups


# ------------------------------------------------------------------
# 1. Unanswered emails
# ------------------------------------------------------------------

async def _detect_unanswered_emails(
    db: ContextEventRepository,
    user_id: UUID,
    now: datetime,
) -> List[Dict[str, Any]]:
    """Find emails received 48h+ ago with no reply from user.

    Checks for a matching email_sent event to the same thread or person
    after the received email timestamp.
    """
    followups: List[Dict[str, Any]] = []

    try:
        received = await db.query_events(
            user_id=user_id,
            event_types=["email_received"],
            since=now - timedelta(days=7),
            until=now - timedelta(hours=48),
            limit=50,
        )
    except Exception:
        return followups

    if not received:
        return followups

    # Load sent emails in the same period for cross-referencing
    try:
        sent = await db.query_events(
            user_id=user_id,
            event_types=["email_sent"],
            since=now - timedelta(days=7),
            until=now,
            limit=200,
        )
    except Exception:
        sent = []

    # Build a set of (thread_id, person) pairs that have been replied to
    replied_threads: Set[str] = set()
    replied_people: Set[str] = set()
    for s in (sent or []):
        sd = getattr(s, "structured_data", None) or {}
        thread_id = sd.get("thread_id") or sd.get("message_id") or ""
        if thread_id:
            replied_threads.add(thread_id.lower())
        for person in (getattr(s, "extracted_people", None) or []):
            replied_people.add(person.lower())

    for ev in received:
        sd = getattr(ev, "structured_data", None) or {}
        thread_id = sd.get("thread_id") or sd.get("message_id") or ""
        people = getattr(ev, "extracted_people", None) or []
        sender = people[0] if people else sd.get("from", "Unknown")

        # Check if replied
        if thread_id and thread_id.lower() in replied_threads:
            continue
        if sender and sender.lower() in replied_people:
            continue

        content = (getattr(ev, "content", None) or "")[:100]
        days_ago = (now - getattr(ev, "timestamp", now)).days

        followups.append({
            "type": "unanswered_email",
            "priority": "high" if days_ago >= 4 else "medium",
            "title": f"Unanswered email from {sender}",
            "description": f"Received {days_ago} day(s) ago: {content}",
            "person": sender,
            "related_event_id": str(getattr(ev, "id", "")),
            "suggested_action": f"Reply to email from {sender}",
            "detected_at": now.isoformat(),
        })

    return followups[:10]


# ------------------------------------------------------------------
# 2. Meeting without follow-up
# ------------------------------------------------------------------

async def _detect_meeting_followups(
    db: ContextEventRepository,
    user_id: UUID,
    now: datetime,
) -> List[Dict[str, Any]]:
    """Find meetings that ended 24h+ ago where commitments were made
    but no email/message was sent to attendees afterward.
    """
    followups: List[Dict[str, Any]] = []

    try:
        meetings = await db.query_events(
            user_id=user_id,
            event_types=["calendar_event", "meeting", "meeting_transcript"],
            since=now - timedelta(days=5),
            until=now - timedelta(hours=24),
            limit=20,
        )
    except Exception:
        return followups

    if not meetings:
        return followups

    # Load outbound communications in the follow-up window
    try:
        outbound = await db.query_events(
            user_id=user_id,
            event_types=["email_sent", "slack_message", "message"],
            since=now - timedelta(days=5),
            until=now,
            limit=200,
        )
    except Exception:
        outbound = []

    outbound_people: Set[str] = set()
    for ev in (outbound or []):
        for person in (getattr(ev, "extracted_people", None) or []):
            outbound_people.add(person.lower())

    for meeting in meetings:
        attendees = getattr(meeting, "extracted_people", None) or []
        sd = getattr(meeting, "structured_data", None) or {}
        action_items = sd.get("action_items") or sd.get("commitments") or []
        content = (getattr(meeting, "content", None) or "Meeting")[:80]
        meeting_ts = getattr(meeting, "timestamp", now)

        if not attendees:
            continue

        # Check if any attendee received a follow-up
        attendees_lower = {a.lower() for a in attendees}
        followed_up = attendees_lower & outbound_people

        if followed_up == attendees_lower:
            continue  # All attendees got follow-up

        unfollowed = attendees_lower - followed_up
        days_ago = (now - meeting_ts).days

        priority = "high" if (action_items and days_ago >= 2) else "medium"

        followups.append({
            "type": "meeting_followup",
            "priority": priority,
            "title": f"Follow up on: {content}",
            "description": (
                f"Meeting {days_ago} day(s) ago with {', '.join(list(unfollowed)[:3])}. "
                f"{len(action_items)} action item(s) noted."
            ),
            "person": list(unfollowed)[0] if unfollowed else None,
            "related_event_id": str(getattr(meeting, "id", "")),
            "suggested_action": (
                f"Send meeting notes to {', '.join(list(unfollowed)[:3])}"
            ),
            "detected_at": now.isoformat(),
        })

    return followups[:10]


# ------------------------------------------------------------------
# 3. Stale conversations
# ------------------------------------------------------------------

async def _detect_stale_conversations(
    db: ContextEventRepository,
    user_id: UUID,
    now: datetime,
) -> List[Dict[str, Any]]:
    """Find threads where user was last to receive a message 3+ days ago.

    Looks at slack messages, chat messages, and similar inbound events
    where no outbound response was sent in 3+ days.
    """
    followups: List[Dict[str, Any]] = []

    try:
        inbound = await db.query_events(
            user_id=user_id,
            event_types=["slack_message", "message", "email_received"],
            since=now - timedelta(days=10),
            until=now - timedelta(days=3),
            limit=50,
        )
    except Exception:
        return followups

    if not inbound:
        return followups

    # Load outbound in the same window
    try:
        outbound = await db.query_events(
            user_id=user_id,
            event_types=["email_sent", "slack_message", "message"],
            since=now - timedelta(days=10),
            until=now,
            limit=200,
        )
    except Exception:
        outbound = []

    # Track people we have responded to recently
    responded_people: Set[str] = set()
    for ev in (outbound or []):
        etype = getattr(ev, "event_type", "")
        # Only count events that are outbound (sent)
        sd = getattr(ev, "structured_data", None) or {}
        direction = sd.get("direction", "")
        if etype == "email_sent" or direction == "outbound":
            for person in (getattr(ev, "extracted_people", None) or []):
                responded_people.add(person.lower())

    seen_people: Set[str] = set()
    for ev in inbound:
        people = getattr(ev, "extracted_people", None) or []
        for person in people:
            if person.lower() in responded_people:
                continue
            if person.lower() in seen_people:
                continue
            seen_people.add(person.lower())

            content = (getattr(ev, "content", None) or "")[:100]
            days_ago = (now - getattr(ev, "timestamp", now)).days

            followups.append({
                "type": "stale_conversation",
                "priority": "low" if days_ago <= 5 else "medium",
                "title": f"Stale thread with {person}",
                "description": (
                    f"Last message from {person} was {days_ago} day(s) ago: {content}"
                ),
                "person": person,
                "related_event_id": str(getattr(ev, "id", "")),
                "suggested_action": f"Check in with {person}",
                "detected_at": now.isoformat(),
            })

    return followups[:10]


# ------------------------------------------------------------------
# 4. Commitment reminders
# ------------------------------------------------------------------

async def _detect_commitment_reminders(
    db: ContextEventRepository,
    user_id: UUID,
    now: datetime,
) -> List[Dict[str, Any]]:
    """Find commitments due within 48h that haven't had related activity."""
    followups: List[Dict[str, Any]] = []

    try:
        commitments = await db.query_events(
            user_id=user_id,
            event_types=["commitment"],
            since=now - timedelta(days=30),
            until=now + timedelta(days=30),
            limit=100,
        )
    except Exception:
        return followups

    if not commitments:
        return followups

    # Load recent activity (last 48h) to check for related work
    try:
        recent_activity = await db.query_events(
            user_id=user_id,
            since=now - timedelta(hours=48),
            until=now,
            limit=200,
        )
    except Exception:
        recent_activity = []

    # Build keyword sets from recent activity
    recent_keywords: Set[str] = set()
    for ev in (recent_activity or []):
        content = (getattr(ev, "content", None) or "").lower()
        words = set(content.split())
        recent_keywords.update(w for w in words if len(w) > 4)

    for commitment in commitments:
        sd = getattr(commitment, "structured_data", None) or {}
        status = sd.get("status", "open")
        if status in ("fulfilled", "completed", "done"):
            continue

        due_str = sd.get("due_date") or sd.get("due")
        if not due_str:
            continue

        try:
            due_dt = datetime.fromisoformat(due_str)
        except (ValueError, TypeError):
            continue

        # Only commitments due within the next 48h
        hours_until_due = (due_dt - now).total_seconds() / 3600
        if hours_until_due < 0 or hours_until_due > 48:
            continue

        # Check if there has been related activity
        content = (getattr(commitment, "content", None) or "")
        commitment_words = set(content.lower().split())
        significant_words = {w for w in commitment_words if len(w) > 4}
        overlap = significant_words & recent_keywords

        if overlap and len(overlap) >= 2:
            continue  # Likely being worked on

        people = getattr(commitment, "extracted_people", None) or []
        person = people[0] if people else None

        priority = "high" if hours_until_due <= 24 else "medium"

        followups.append({
            "type": "commitment_due",
            "priority": priority,
            "title": f"Commitment due soon: {content[:60]}",
            "description": (
                f"Due in {int(hours_until_due)} hour(s). "
                f"No related activity detected in the last 48h."
            ),
            "person": person,
            "related_event_id": str(getattr(commitment, "id", "")),
            "suggested_action": f"Work on or reschedule: {content[:60]}",
            "detected_at": now.isoformat(),
        })

    return followups[:10]
