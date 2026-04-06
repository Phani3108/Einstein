"""Reflection and review API routes.

Weekly and monthly review workflows, person relationship analysis,
and commitment journal — all auto-populated from context events.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.llm.llm_service import LLMService
from src.domain.entities.user import User


# ---- Response Models ----

class RelationshipStrength(BaseModel):
    person_id: str
    name: str
    score: float  # 0-1, composite of recency × frequency × depth
    recency_score: float
    frequency_score: float
    depth_score: float
    trend: str = "stable"  # strengthening, stable, fading
    last_seen: Optional[datetime]
    interaction_count: int
    top_topics: List[str] = []
    open_commitments: int = 0


class PersonDossier(BaseModel):
    """Complete intelligence package for a person — used before meetings."""
    person_id: str
    name: str
    role: Optional[str]
    organization: Optional[str]
    relationship_strength: float
    recent_events: List[Dict[str, Any]] = []
    shared_topics: List[str] = []
    open_commitments: List[Dict[str, Any]] = []
    interaction_timeline: List[Dict[str, Any]] = []
    suggested_talking_points: List[str] = []


class WeeklyReviewData(BaseModel):
    period: str
    events_captured: int
    notes_created: int = 0
    new_connections: int
    active_projects: List[Dict[str, Any]] = []
    stale_projects: List[Dict[str, Any]] = []
    completed_commitments: List[Dict[str, Any]] = []
    overdue_commitments: List[Dict[str, Any]] = []
    people_interacted: List[Dict[str, Any]] = []
    fading_relationships: List[Dict[str, Any]] = []
    top_topics: List[Dict[str, Any]] = []
    reflection_prompts: List[str] = []
    ai_summary: str = ""


class MonthlyReflection(BaseModel):
    period: str
    total_events: int
    themes: List[Dict[str, Any]] = []
    idea_evolution: List[str] = []
    decision_journal: List[Dict[str, Any]] = []
    relationship_changes: List[Dict[str, Any]] = []
    patterns: List[str] = []
    ai_reflection: str = ""


# ---- LLM Prompts ----

WEEKLY_REVIEW_SYSTEM = """You are Einstein, a personal context intelligence assistant.
Generate a thoughtful weekly review based on the user's activity data.
Return ONLY valid JSON:
{
  "summary": "2-3 paragraph narrative of the week",
  "reflection_prompts": [
    "What went well this week?",
    "What could have gone better?",
    "What will you focus on next week?"
  ]
}
Be warm, insightful, and specific to the data. Mention people and projects by name."""

MONTHLY_REFLECTION_SYSTEM = """You are Einstein, a personal context intelligence assistant.
Generate a meaningful monthly reflection from the user's activity patterns.
Return ONLY valid JSON:
{
  "reflection": "3-4 paragraph thoughtful reflection on the month",
  "patterns": ["Pattern 1 observed", "Pattern 2 observed"],
  "idea_evolution": ["How ideas developed over the month"]
}
Be insightful about trends, not just factual. Notice shifts in focus, emerging themes, fading interests."""

TALKING_POINTS_SYSTEM = """You are Einstein, a personal context intelligence assistant.
Based on the interaction history with this person, suggest 3-5 relevant talking points.
Return ONLY valid JSON:
{
  "talking_points": ["Point 1", "Point 2", "Point 3"]
}
Be specific and actionable. Reference actual events and topics."""


# ---- Router Factory ----

def create_reflection_router(
    context_repo: ContextEventRepository,
    llm_service: LLMService,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/reflection", tags=["reflection"])

    # ---- Relationship Strength ----

    @router.get("/relationships", response_model=List[RelationshipStrength])
    async def get_relationship_strengths(
        limit: int = Query(default=20, le=50),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get relationship strength scores for all people, ranked by strength."""
        people = await context_repo.get_people(user.id, limit=limit)
        now = datetime.now()

        results = []
        for person in people:
            # Recency: how recently they were seen (exponential decay, 7-day half-life)
            last_active = person.last_activity_at or person.last_seen
            if last_active:
                days_since = (now - last_active).total_seconds() / 86400
                import math
                recency = math.exp(-0.1 * days_since)  # faster decay than freshness
            else:
                recency = 0.0

            # Frequency: interaction count normalized (log scale)
            import math
            frequency = min(1.0, math.log1p(person.interaction_count) / 5.0)

            # Depth: based on topics shared (more topics = deeper relationship)
            all_events = await context_repo.get_events(user_id=user.id, limit=200)
            person_events = [
                e for e in all_events
                if person.name.lower() in (e.content or "").lower()
                or person.name in (e.extracted_people or [])
            ]
            topics = set()
            for e in person_events:
                topics.update(e.topics or [])
            depth = min(1.0, len(topics) / 5.0)

            # Composite score
            score = (recency * 0.4) + (frequency * 0.35) + (depth * 0.25)

            # Trend: compare current score to what it would have been 14 days ago
            if person.interaction_count > 5 and recency < 0.3:
                trend = "fading"
            elif person.interaction_count > 0 and recency > 0.7:
                trend = "strengthening"
            else:
                trend = "stable"

            # Open commitments count
            commitments = await context_repo.get_commitments(user.id, status="open")
            open_commits = len([
                c for c in commitments
                if person.name.lower() in c.description.lower()
            ])

            results.append(RelationshipStrength(
                person_id=str(person.id),
                name=person.name,
                score=round(score, 3),
                recency_score=round(recency, 3),
                frequency_score=round(frequency, 3),
                depth_score=round(depth, 3),
                trend=trend,
                last_seen=person.last_seen,
                interaction_count=person.interaction_count,
                top_topics=list(topics)[:5],
                open_commitments=open_commits,
            ))

        # Sort by composite score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    # ---- Person Dossier ----

    @router.get("/people/{person_id}/dossier", response_model=PersonDossier)
    async def get_person_dossier(
        person_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a complete intelligence package for a person — ideal before meetings."""
        people = await context_repo.get_people(user.id)
        person = next((p for p in people if str(p.id) == person_id), None)
        if not person:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Person not found")

        # Get all events mentioning this person (last 90 days)
        since = datetime.now() - timedelta(days=90)
        all_events = await context_repo.get_events(user_id=user.id, since=since, limit=300)
        person_events = [
            e for e in all_events
            if person.name.lower() in (e.content or "").lower()
            or person.name in (e.extracted_people or [])
        ]

        # Shared topics
        topics: Dict[str, int] = {}
        for e in person_events:
            for t in (e.topics or []):
                topics[t] = topics.get(t, 0) + 1
        shared_topics = [t for t, _ in sorted(topics.items(), key=lambda x: -x[1])[:10]]

        # Open commitments involving this person
        all_commitments = await context_repo.get_commitments(user.id, status="open")
        person_commitments = [
            {"description": c.description, "due_date": c.due_date.isoformat() if c.due_date else None, "status": c.status}
            for c in all_commitments
            if person.name.lower() in c.description.lower()
        ]

        # Interaction timeline (last 10 events)
        timeline = [
            {
                "date": e.timestamp.isoformat()[:10],
                "source": e.source,
                "type": e.event_type,
                "summary": (e.content or "")[:150],
            }
            for e in person_events[:10]
        ]

        # Recent events summary
        recent = [
            {
                "date": e.timestamp.isoformat()[:10],
                "source": e.source,
                "content": (e.content or "")[:200],
            }
            for e in person_events[:5]
        ]

        # Relationship strength
        import math
        last_active = person.last_activity_at or person.last_seen
        recency = math.exp(-0.1 * ((datetime.now() - last_active).total_seconds() / 86400)) if last_active else 0.0
        frequency = min(1.0, math.log1p(person.interaction_count) / 5.0)
        depth = min(1.0, len(shared_topics) / 5.0)
        strength = (recency * 0.4) + (frequency * 0.35) + (depth * 0.25)

        # Generate talking points via LLM
        suggested_points = []
        if person_events:
            events_text = "\n".join(
                f"[{e.source}] {e.timestamp.isoformat()[:10]}: {(e.content or '')[:150]}"
                for e in person_events[:10]
            )
            prompt = f"Person: {person.name} ({person.role or 'unknown role'} at {person.organization or 'unknown org'})\n\nRecent interactions:\n{events_text}\n\nOpen commitments: {len(person_commitments)}"
            try:
                raw = await llm_service.generate(prompt, system_prompt=TALKING_POINTS_SYSTEM)
                data = json.loads(raw)
                suggested_points = data.get("talking_points", [])
            except Exception:
                suggested_points = []

        return PersonDossier(
            person_id=str(person.id),
            name=person.name,
            role=person.role,
            organization=person.organization,
            relationship_strength=round(strength, 3),
            recent_events=recent,
            shared_topics=shared_topics,
            open_commitments=person_commitments,
            interaction_timeline=timeline,
            suggested_talking_points=suggested_points,
        )

    # ---- Weekly Review ----

    @router.get("/review/weekly", response_model=WeeklyReviewData)
    async def get_weekly_review(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get auto-populated weekly review data."""
        now = datetime.now()
        since = now - timedelta(days=7)

        events = await context_repo.get_events(user_id=user.id, since=since, limit=500)
        people = await context_repo.get_people(user.id, limit=50)
        connections = await context_repo.get_connections(user_id=user.id, limit=500)
        commitments = await context_repo.get_commitments(user.id)

        # Topic aggregation
        topic_counts: Dict[str, int] = {}
        for e in events:
            for t in (e.topics or []):
                topic_counts[t] = topic_counts.get(t, 0) + 1
        top_topics = [{"topic": t, "count": c} for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]]

        # Projects status
        all_projects_active = await context_repo.get_projects(user.id, status="active")
        stale_projects = await context_repo.get_dormant_projects(user.id, min_days=7)

        active_projects = [
            {"title": p.title, "status": p.status, "dormancy_days": p.dormancy_days}
            for p in all_projects_active
        ]
        stale = [
            {"title": p.title, "dormancy_days": p.dormancy_days}
            for p in stale_projects
        ]

        # Commitments
        completed = [
            {"description": c.description, "created_at": c.created_at.isoformat()[:10]}
            for c in commitments if c.status == "fulfilled"
            and c.updated_at and c.updated_at >= since
        ]
        overdue = [
            {"description": c.description, "due_date": c.due_date.isoformat()[:10] if c.due_date else None,
             "days_overdue": (now - c.due_date).days if c.due_date else 0}
            for c in commitments if c.status == "overdue"
        ]

        # People interacted with this week
        active_people = [
            p for p in people
            if p.last_seen and p.last_seen >= since
        ]
        people_interacted = [
            {"name": p.name, "interaction_count": p.interaction_count, "role": p.role}
            for p in active_people[:10]
        ]

        # Fading relationships
        fading = [
            {"name": p.name, "dormancy_days": p.dormancy_days, "freshness_score": p.freshness_score}
            for p in people
            if p.dormancy_days > 21
        ][:5]

        # New connections this week
        new_conns = len([c for c in connections if c.discovered_at >= since])

        # Generate AI summary + reflection prompts
        ai_summary = ""
        reflection_prompts = [
            "What went well this week?",
            "What could have gone better?",
            "What will you focus on next week?",
            "Who should you follow up with?",
            "Any decisions that need revisiting?",
        ]

        if events:
            context = f"""Week: {since.isoformat()[:10]} to {now.isoformat()[:10]}
Events: {len(events)} from {len(set(e.source for e in events))} sources
Top topics: {', '.join(t['topic'] for t in top_topics[:5])}
Active projects: {len(active_projects)}
Stale projects: {len(stale)}
Completed commitments: {len(completed)}
Overdue commitments: {len(overdue)}
People interacted: {', '.join(p['name'] for p in people_interacted[:5])}
Fading relationships: {', '.join(f['name'] for f in fading)}"""

            try:
                raw = await llm_service.generate(context, system_prompt=WEEKLY_REVIEW_SYSTEM)
                data = json.loads(raw)
                ai_summary = data.get("summary", "")
                reflection_prompts = data.get("reflection_prompts", reflection_prompts)
            except Exception:
                ai_summary = f"This week: {len(events)} events, {len(active_projects)} active projects, {len(people_interacted)} people interacted."

        return WeeklyReviewData(
            period=f"{since.isoformat()[:10]} to {now.isoformat()[:10]}",
            events_captured=len(events),
            new_connections=new_conns,
            active_projects=active_projects,
            stale_projects=stale,
            completed_commitments=completed,
            overdue_commitments=overdue,
            people_interacted=people_interacted,
            fading_relationships=fading,
            top_topics=top_topics,
            reflection_prompts=reflection_prompts,
            ai_summary=ai_summary,
        )

    # ---- Monthly Reflection ----

    @router.get("/review/monthly", response_model=MonthlyReflection)
    async def get_monthly_reflection(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get AI-generated monthly reflection with pattern detection."""
        now = datetime.now()
        since = now - timedelta(days=30)

        events = await context_repo.get_events(user_id=user.id, since=since, limit=500)
        people = await context_repo.get_people(user.id, limit=50)
        commitments = await context_repo.get_commitments(user.id)

        # Theme analysis: topics across the month
        topic_counts: Dict[str, int] = {}
        for e in events:
            for t in (e.topics or []):
                topic_counts[t] = topic_counts.get(t, 0) + 1
        themes = [{"theme": t, "count": c} for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])[:15]]

        # Relationship changes
        relationship_changes = []
        for p in people:
            if p.dormancy_days > 21:
                relationship_changes.append({
                    "name": p.name,
                    "change": "fading",
                    "dormancy_days": p.dormancy_days,
                })
            elif p.interaction_count > 10 and p.freshness_score > 0.8:
                relationship_changes.append({
                    "name": p.name,
                    "change": "strengthening",
                    "interaction_count": p.interaction_count,
                })

        # Decision journal: commitments that were fulfilled or went overdue
        decisions = [
            {
                "description": c.description,
                "status": c.status,
                "created": c.created_at.isoformat()[:10],
                "due": c.due_date.isoformat()[:10] if c.due_date else None,
            }
            for c in commitments
            if c.created_at >= since
        ]

        # Generate AI reflection
        ai_reflection = ""
        patterns = []
        idea_evolution = []

        if events:
            context = f"""Month: {since.isoformat()[:10]} to {now.isoformat()[:10]}
Total events: {len(events)}
Top themes: {', '.join(t['theme'] for t in themes[:8])}
Relationship changes: {len(relationship_changes)} (strengthening/fading)
Commitments created: {len(decisions)}
Sources: {dict((e.source, 0) for e in events).keys()}"""

            try:
                raw = await llm_service.generate(context, system_prompt=MONTHLY_REFLECTION_SYSTEM)
                data = json.loads(raw)
                ai_reflection = data.get("reflection", "")
                patterns = data.get("patterns", [])
                idea_evolution = data.get("idea_evolution", [])
            except Exception:
                ai_reflection = f"Over the past month, you captured {len(events)} events across {len(set(e.source for e in events))} sources."

        return MonthlyReflection(
            period=f"{since.isoformat()[:10]} to {now.isoformat()[:10]}",
            total_events=len(events),
            themes=themes,
            idea_evolution=idea_evolution,
            decision_journal=decisions,
            relationship_changes=relationship_changes,
            patterns=patterns,
            ai_reflection=ai_reflection,
        )

    # ---- Person Merge ----

    @router.post("/people/merge")
    async def merge_people(
        source_id: str,
        target_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Merge two person profiles (e.g., WhatsApp 'Mom' = Contact 'Jane Doe').

        The target person absorbs the source person's aliases.
        """
        people = await context_repo.get_people(user.id)
        source = next((p for p in people if str(p.id) == source_id), None)
        target = next((p for p in people if str(p.id) == target_id), None)

        if not source or not target:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Person not found")

        # Merge aliases: add source name and its aliases to target
        merged_aliases = list(set(
            (target.aliases or []) + (source.aliases or []) + [source.name]
        ))

        # Update target with merged data
        from src.domain.entities.context_event import PersonProfile
        import uuid

        merged = PersonProfile(
            id=target.id,
            user_id=target.user_id,
            name=target.name,
            aliases=merged_aliases,
            phone=target.phone or source.phone,
            email=target.email or source.email,
            role=target.role or source.role,
            organization=target.organization or source.organization,
            last_seen=max(filter(None, [target.last_seen, source.last_seen]), default=None),
            interaction_count=target.interaction_count + source.interaction_count,
            notes="\n".join(filter(None, [target.notes, source.notes])),
            freshness_score=max(target.freshness_score, source.freshness_score),
            last_activity_at=max(filter(None, [target.last_activity_at, source.last_activity_at]), default=None),
        )

        await context_repo.upsert_person(merged)

        return {
            "merged_into": str(target.id),
            "absorbed": str(source.id),
            "new_aliases": merged_aliases,
            "combined_interactions": merged.interaction_count,
        }

    return router
