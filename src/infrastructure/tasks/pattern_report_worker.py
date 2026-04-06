"""Weekly pattern report worker — generates analytics and trend reports.

Designed to be invoked by arq, celery, or a simple async scheduler.
Typically runs Sunday evening or Monday morning and produces a
comprehensive weekly digest covering communication, commitments,
projects, relationships, and time patterns.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from uuid import UUID

from src.infrastructure.repositories.context_event_repository import ContextEventRepository

logger = logging.getLogger(__name__)


async def pattern_report_task(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the weekly pattern report for a user.

    Args:
        ctx: Worker context dict.  Expected keys:
            - ``context_repo`` — a ``ContextEventRepository`` instance.
            - ``user_id`` — UUID of the user.

    Returns:
        A weekly report dict.
    """
    context_repo: ContextEventRepository = ctx["context_repo"]
    user_id = ctx["user_id"]

    try:
        return await generate_weekly_report(context_repo, user_id)
    except Exception as exc:
        logger.error("Failed to generate weekly report for %s: %s", user_id, exc)
        return {"error": str(exc), "generated_at": datetime.utcnow().isoformat()}


async def generate_weekly_report(
    db: ContextEventRepository,
    user_id: UUID,
) -> Dict[str, Any]:
    """Generate a comprehensive weekly analytics and pattern report.

    Analyses communication volume, commitment health, project activity,
    relationship trends, and time-of-day patterns for the past week
    compared to the prior week.

    Args:
        db: The context event repository.
        user_id: User to generate the report for.

    Returns:
        A structured report dict.
    """
    now = datetime.utcnow()
    week_start = now - timedelta(days=7)
    prior_week_start = now - timedelta(days=14)

    # Fetch this week and last week events in bulk
    this_week_events = await _safe_query(
        db, user_id, since=week_start, until=now, limit=1000
    )
    last_week_events = await _safe_query(
        db, user_id, since=prior_week_start, until=week_start, limit=1000
    )

    communication = _analyse_communication(this_week_events, last_week_events)
    commitments = await _analyse_commitments(db, user_id, this_week_events, now)
    projects = await _analyse_projects(db, user_id, this_week_events, last_week_events)
    relationships = _analyse_relationships(this_week_events, last_week_events, now)
    time_patterns = _analyse_time_patterns(this_week_events)

    return {
        "week_start": week_start.date().isoformat(),
        "week_end": now.date().isoformat(),
        "communication": communication,
        "commitments": commitments,
        "projects": projects,
        "relationships": relationships,
        "time_patterns": time_patterns,
        "generated_at": now.isoformat(),
    }


# ------------------------------------------------------------------
# Communication analysis
# ------------------------------------------------------------------

def _analyse_communication(
    this_week: list, last_week: list
) -> Dict[str, Any]:
    """Compute communication volume by source and top contacts."""
    tw_by_source: Counter = Counter()
    lw_by_source: Counter = Counter()
    tw_people: Counter = Counter()

    for ev in this_week:
        source = getattr(ev, "source", "unknown") or "unknown"
        tw_by_source[source] += 1
        for person in (getattr(ev, "extracted_people", None) or []):
            tw_people[person] += 1

    for ev in last_week:
        source = getattr(ev, "source", "unknown") or "unknown"
        lw_by_source[source] += 1

    lw_people: Counter = Counter()
    for ev in last_week:
        for person in (getattr(ev, "extracted_people", None) or []):
            lw_people[person] += 1

    # Percent change per source
    all_sources = set(tw_by_source.keys()) | set(lw_by_source.keys())
    vs_last_week: Dict[str, str] = {}
    for src in all_sources:
        tw_count = tw_by_source.get(src, 0)
        lw_count = lw_by_source.get(src, 0)
        if lw_count == 0:
            vs_last_week[src] = "+100%" if tw_count > 0 else "0%"
        else:
            pct = round(((tw_count - lw_count) / lw_count) * 100)
            sign = "+" if pct > 0 else ""
            vs_last_week[src] = f"{sign}{pct}%"

    # Top contacts with trend
    top_contacts: List[Dict[str, Any]] = []
    for person, count in tw_people.most_common(5):
        lw_count = lw_people.get(person, 0)
        if count > lw_count:
            trend = "up"
        elif count < lw_count:
            trend = "down"
        else:
            trend = "stable"
        top_contacts.append({"name": person, "count": count, "trend": trend})

    return {
        "total_events": len(this_week),
        "by_source": dict(tw_by_source),
        "vs_last_week": vs_last_week,
        "top_contacts": top_contacts,
    }


# ------------------------------------------------------------------
# Commitment health
# ------------------------------------------------------------------

async def _analyse_commitments(
    db: ContextEventRepository,
    user_id: UUID,
    this_week_events: list,
    now: datetime,
) -> Dict[str, Any]:
    """Analyse commitment creation, fulfillment, and overdue status."""
    created = 0
    fulfilled = 0
    overdue = 0
    overdue_list: List[Dict[str, str]] = []
    fulfillment_days: List[float] = []

    try:
        commitments = await db.query_events(
            user_id=user_id,
            event_types=["commitment"],
            since=now - timedelta(days=30),
            until=now + timedelta(days=7),
            limit=200,
        )
    except Exception:
        commitments = []

    week_start = now - timedelta(days=7)

    for c in commitments:
        ts = getattr(c, "timestamp", None)
        sd = getattr(c, "structured_data", None) or {}
        status = sd.get("status", "open")
        due_str = sd.get("due_date") or sd.get("due")
        content = (getattr(c, "content", None) or "")[:150]

        # Created this week?
        if ts and ts >= week_start:
            created += 1

        # Fulfilled this week?
        if status in ("fulfilled", "completed", "done"):
            fulfilled_at = sd.get("fulfilled_at") or sd.get("completed_at")
            if fulfilled_at:
                try:
                    f_dt = datetime.fromisoformat(fulfilled_at)
                    if f_dt >= week_start:
                        fulfilled += 1
                    if ts:
                        fulfillment_days.append((f_dt - ts).total_seconds() / 86400)
                except (ValueError, TypeError):
                    pass
            else:
                fulfilled += 1
            continue

        # Overdue?
        if due_str:
            try:
                due_dt = datetime.fromisoformat(due_str)
                if due_dt < now and status not in ("fulfilled", "completed", "done"):
                    overdue += 1
                    people = getattr(c, "extracted_people", None) or []
                    overdue_list.append({
                        "content": content,
                        "person": people[0] if people else "",
                        "due": due_str,
                    })
            except (ValueError, TypeError):
                pass

    avg_fulfillment = (
        round(sum(fulfillment_days) / len(fulfillment_days), 1)
        if fulfillment_days
        else None
    )

    return {
        "created": created,
        "fulfilled": fulfilled,
        "overdue": overdue,
        "overdue_list": overdue_list[:10],
        "avg_time_to_fulfillment_days": avg_fulfillment,
    }


# ------------------------------------------------------------------
# Project activity
# ------------------------------------------------------------------

async def _analyse_projects(
    db: ContextEventRepository,
    user_id: UUID,
    this_week: list,
    last_week: list,
) -> Dict[str, Any]:
    """Analyse per-project activity and staleness."""
    try:
        all_projects = await db.get_projects(user_id)
    except Exception:
        all_projects = []

    if not all_projects:
        return {"most_active": [], "declining": [], "stale": []}

    # Map project names to event counts
    tw_counts: Counter = Counter()
    lw_counts: Counter = Counter()

    project_names = {
        (getattr(p, "title", "") or getattr(p, "name", "") or "").lower(): p
        for p in all_projects
    }

    def _match_project(event: Any) -> str | None:
        """Try to match an event to a project by content or structured_data."""
        sd = getattr(event, "structured_data", None) or {}
        proj_name = sd.get("project") or sd.get("project_name") or ""
        if proj_name and proj_name.lower() in project_names:
            return proj_name.lower()
        # Fall back to content keyword match
        content = (getattr(event, "content", None) or "").lower()
        for pn in project_names:
            if pn and pn in content:
                return pn
        return None

    for ev in this_week:
        pn = _match_project(ev)
        if pn:
            tw_counts[pn] += 1

    for ev in last_week:
        pn = _match_project(ev)
        if pn:
            lw_counts[pn] += 1

    most_active = [
        {"title": pn, "event_count": count}
        for pn, count in tw_counts.most_common(5)
    ]

    declining = []
    stale = []
    for pn, proj in project_names.items():
        tw = tw_counts.get(pn, 0)
        lw = lw_counts.get(pn, 0)
        if lw > 0 and tw < lw:
            declining.append({"title": pn, "this_week": tw, "last_week": lw})
        if tw == 0 and lw == 0:
            last_activity = getattr(proj, "updated_at", None) or getattr(proj, "created_at", None)
            stale.append({
                "title": pn,
                "last_activity": last_activity.isoformat() if last_activity else "unknown",
            })

    declining.sort(key=lambda x: x["last_week"] - x["this_week"], reverse=True)

    return {
        "most_active": most_active,
        "declining": declining[:5],
        "stale": stale[:5],
    }


# ------------------------------------------------------------------
# Relationship health
# ------------------------------------------------------------------

def _analyse_relationships(
    this_week: list, last_week: list, now: datetime
) -> Dict[str, Any]:
    """Analyse relationship trends — growing, cooling, dormant."""
    tw_people: Counter = Counter()
    lw_people: Counter = Counter()
    last_seen: Dict[str, datetime] = {}

    for ev in this_week:
        for person in (getattr(ev, "extracted_people", None) or []):
            tw_people[person] += 1
            ts = getattr(ev, "timestamp", None)
            if ts and (person not in last_seen or ts > last_seen[person]):
                last_seen[person] = ts

    for ev in last_week:
        for person in (getattr(ev, "extracted_people", None) or []):
            lw_people[person] += 1
            ts = getattr(ev, "timestamp", None)
            if ts and (person not in last_seen or ts > last_seen[person]):
                last_seen[person] = ts

    all_people = set(tw_people.keys()) | set(lw_people.keys())

    growing: List[Dict[str, Any]] = []
    cooling: List[Dict[str, Any]] = []
    dormant: List[Dict[str, Any]] = []

    for person in all_people:
        tw = tw_people.get(person, 0)
        lw = lw_people.get(person, 0)

        if tw > lw and tw >= 2:
            growing.append({"name": person, "this_week": tw, "last_week": lw})
        elif lw > tw and lw >= 2:
            cooling.append({"name": person, "this_week": tw, "last_week": lw})

        # Dormant: not contacted in 14+ days
        ls = last_seen.get(person)
        if ls:
            days_silent = (now - ls).days
            if days_silent >= 14:
                dormant.append({
                    "name": person,
                    "last_contact": ls.isoformat(),
                    "days_silent": days_silent,
                })

    growing.sort(key=lambda x: x["this_week"] - x["last_week"], reverse=True)
    cooling.sort(key=lambda x: x["last_week"] - x["this_week"], reverse=True)
    dormant.sort(key=lambda x: x["days_silent"], reverse=True)

    return {
        "growing": growing[:5],
        "cooling": cooling[:5],
        "dormant": dormant[:10],
    }


# ------------------------------------------------------------------
# Time patterns
# ------------------------------------------------------------------

def _analyse_time_patterns(this_week: list) -> Dict[str, Any]:
    """Analyse peak hours, peak days, and meeting load."""
    hour_counts: Counter = Counter()
    day_counts: Counter = Counter()
    meeting_minutes: float = 0.0

    for ev in this_week:
        ts = getattr(ev, "timestamp", None)
        if ts:
            hour_counts[ts.hour] += 1
            day_counts[ts.strftime("%A")] += 1

        etype = getattr(ev, "event_type", "")
        if etype in ("calendar_event", "meeting", "meeting_transcript"):
            sd = getattr(ev, "structured_data", None) or {}
            duration = sd.get("duration_minutes") or sd.get("duration")
            if duration:
                try:
                    meeting_minutes += float(duration)
                except (ValueError, TypeError):
                    meeting_minutes += 30  # default assumption
            else:
                meeting_minutes += 30

    # Top 3 peak hours
    peak_hours = [h for h, _ in hour_counts.most_common(3)]
    # Top 3 peak days
    peak_days = [d for d, _ in day_counts.most_common(3)]

    return {
        "peak_hours": peak_hours,
        "peak_days": peak_days,
        "meeting_hours": round(meeting_minutes / 60, 1),
    }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _safe_query(
    db: ContextEventRepository,
    user_id: UUID,
    since: datetime,
    until: datetime,
    limit: int = 1000,
) -> list:
    """Query events with error handling."""
    try:
        events = await db.query_events(
            user_id=user_id,
            since=since,
            until=until,
            limit=limit,
        )
        return events or []
    except Exception as exc:
        logger.warning("Failed to query events: %s", exc)
        return []
