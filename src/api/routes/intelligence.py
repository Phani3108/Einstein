"""Intelligence layer API routes.

Endpoints for pre-meeting briefings, weekly pattern reports,
follow-up detection, relationship health scoring, and a combined
intelligence summary.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.domain.entities.user import User


# ---- Response Models ----


class AttendeeInteraction(BaseModel):
    type: str
    summary: str
    date: str


class AttendeeCommitment(BaseModel):
    content: str
    due: Optional[str] = None
    status: str = "open"


class AttendeeBriefing(BaseModel):
    name: str
    role: str = ""
    organization: str = ""
    relationship_strength: str
    last_contact: Optional[str] = None
    recent_interactions: List[AttendeeInteraction] = Field(default_factory=list)
    open_commitments: List[AttendeeCommitment] = Field(default_factory=list)
    talking_points: List[str] = Field(default_factory=list)


class RelatedProject(BaseModel):
    title: str
    status: str = "active"
    recent_activity: str = ""


class MeetingBriefingResponse(BaseModel):
    meeting_title: str
    meeting_time: str
    attendees: List[AttendeeBriefing] = Field(default_factory=list)
    related_projects: List[RelatedProject] = Field(default_factory=list)
    suggested_agenda: List[str] = Field(default_factory=list)
    context_summary: str = ""
    generated_at: str


class FollowUpSuggestion(BaseModel):
    type: str
    priority: str
    title: str
    description: str
    person: Optional[str] = None
    related_event_id: Optional[str] = None
    suggested_action: str
    detected_at: str


class RelationshipScoreComponents(BaseModel):
    recency: int = 0
    frequency: int = 0
    diversity: int = 0
    reciprocity: int = 0


class RelationshipScore(BaseModel):
    person_id: str
    person_name: str
    score: int = 0
    grade: str = "dormant"
    components: RelationshipScoreComponents = Field(
        default_factory=RelationshipScoreComponents
    )
    last_interaction: Optional[str] = None
    interaction_count_30d: int = 0
    interaction_count_90d: int = 0
    primary_channel: str = "unknown"
    trend: str = "stable"


class RelationshipDashboardSummary(BaseModel):
    total_contacts: int = 0
    strong: int = 0
    moderate: int = 0
    weak: int = 0
    dormant: int = 0


class RelationshipDashboard(BaseModel):
    summary: RelationshipDashboardSummary = Field(
        default_factory=RelationshipDashboardSummary
    )
    top_relationships: List[RelationshipScore] = Field(default_factory=list)
    declining: List[RelationshipScore] = Field(default_factory=list)
    improving: List[RelationshipScore] = Field(default_factory=list)
    dormant: List[RelationshipScore] = Field(default_factory=list)


class IntelligenceSummary(BaseModel):
    """Combined intelligence summary."""
    upcoming_briefings: List[MeetingBriefingResponse] = Field(default_factory=list)
    pending_followups: List[FollowUpSuggestion] = Field(default_factory=list)
    relationship_alerts: List[RelationshipScore] = Field(default_factory=list)
    generated_at: str


# ---- Router Factory ----


def create_intelligence_router(
    context_repo: ContextEventRepository,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    """Create the intelligence router with injected dependencies.

    Args:
        context_repo: The context event repository for data access.
        auth_middleware: Authentication middleware for securing endpoints.

    Returns:
        A configured APIRouter instance.
    """
    router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

    # Lazy imports to avoid circular dependencies
    from src.infrastructure.tasks.briefing_worker import (
        find_upcoming_meetings,
        generate_pre_meeting_briefing,
    )
    from src.infrastructure.tasks.pattern_report_worker import generate_weekly_report
    from src.infrastructure.tasks.followup_detector import detect_pending_followups
    from src.infrastructure.services.relationship_health import RelationshipHealthService

    relationship_service = RelationshipHealthService()

    # ---- Briefing endpoints ----

    @router.get(
        "/briefing/upcoming",
        response_model=List[MeetingBriefingResponse],
        summary="Get briefings for upcoming meetings",
    )
    async def get_upcoming_briefings(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Generate pre-meeting briefings for meetings in the next 2 hours.

        Returns contextual briefings with attendee information,
        open commitments, relationship strength, and suggested
        talking points for each upcoming meeting.
        """
        try:
            meetings = await find_upcoming_meetings(
                context_repo, user.id, within_minutes=120
            )
            briefings = []
            for meeting in meetings:
                try:
                    briefing = await generate_pre_meeting_briefing(
                        context_repo, user.id, meeting
                    )
                    briefings.append(briefing)
                except Exception:
                    continue
            return briefings
        except Exception as exc:
            raise HTTPException(500, f"Failed to generate briefings: {exc}")

    @router.get(
        "/briefing/{meeting_id}",
        response_model=MeetingBriefingResponse,
        summary="Get briefing for a specific meeting",
    )
    async def get_meeting_briefing(
        meeting_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Generate a pre-meeting briefing for a specific meeting event.

        Args:
            meeting_id: The ID of the calendar/meeting event.
        """
        try:
            # Look up the specific meeting event
            events = await context_repo.query_events(
                user_id=user.id,
                event_types=["calendar_event", "meeting", "meeting_transcript"],
                limit=200,
            )
            meeting = None
            for ev in (events or []):
                if str(getattr(ev, "id", "")) == meeting_id:
                    meeting = ev
                    break

            if not meeting:
                raise HTTPException(404, f"Meeting not found: {meeting_id}")

            briefing = await generate_pre_meeting_briefing(
                context_repo, user.id, meeting
            )
            return briefing
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(500, f"Failed to generate briefing: {exc}")

    # ---- Weekly report endpoints ----

    @router.get(
        "/report/weekly",
        summary="Get latest weekly pattern report",
    )
    async def get_weekly_report(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Retrieve the latest weekly analytics and pattern report.

        Covers communication volume, commitment health, project activity,
        relationship trends, and time-of-day patterns.
        """
        try:
            report = await generate_weekly_report(context_repo, user.id)
            return report
        except Exception as exc:
            raise HTTPException(500, f"Failed to get weekly report: {exc}")

    @router.get(
        "/report/weekly/generate",
        summary="Generate a fresh weekly report",
    )
    async def generate_weekly_report_endpoint(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Trigger generation of a new weekly pattern report.

        This always computes a fresh report regardless of caching.
        """
        try:
            report = await generate_weekly_report(context_repo, user.id)
            return report
        except Exception as exc:
            raise HTTPException(500, f"Failed to generate weekly report: {exc}")

    # ---- Follow-up endpoints ----

    @router.get(
        "/followups",
        response_model=List[FollowUpSuggestion],
        summary="Get pending follow-up suggestions",
    )
    async def get_followups(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Detect and return pending follow-up suggestions.

        Identifies unanswered emails, meetings without follow-up,
        stale conversations, and commitments due soon.
        """
        try:
            followups = await detect_pending_followups(context_repo, user.id)
            return followups
        except Exception as exc:
            raise HTTPException(500, f"Failed to detect follow-ups: {exc}")

    # ---- Relationship endpoints ----

    @router.get(
        "/relationships",
        response_model=RelationshipDashboard,
        summary="Get relationship health dashboard",
    )
    async def get_relationship_dashboard(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a comprehensive relationship health dashboard.

        Returns summary statistics, top relationships, those needing
        attention, improving relationships, and dormant contacts.
        """
        try:
            dashboard = await relationship_service.get_relationship_dashboard(
                context_repo, user.id
            )
            return dashboard
        except Exception as exc:
            raise HTTPException(
                500, f"Failed to get relationship dashboard: {exc}"
            )

    @router.get(
        "/relationships/{person_id}",
        response_model=RelationshipScore,
        summary="Get relationship score for a person",
    )
    async def get_relationship_score(
        person_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a detailed relationship health score for a specific person.

        Computes recency, frequency, diversity, and reciprocity scores
        along with trend information.

        Args:
            person_id: UUID of the person to score.
        """
        try:
            pid = UUID(person_id)
        except ValueError:
            raise HTTPException(400, f"Invalid person_id: {person_id}")

        try:
            score = await relationship_service.compute_relationship_score(
                context_repo, user.id, pid
            )
            return score
        except Exception as exc:
            raise HTTPException(
                500, f"Failed to compute relationship score: {exc}"
            )

    # ---- Combined intelligence summary ----

    @router.get(
        "/insights/summary",
        response_model=IntelligenceSummary,
        summary="Combined intelligence summary",
    )
    async def get_intelligence_summary(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a combined intelligence summary.

        Merges upcoming meeting briefings, pending follow-ups, and
        relationship alerts (declining relationships) into a single
        response for a unified intelligence view.
        """
        now = datetime.utcnow()
        briefings: List[Dict[str, Any]] = []
        followups: List[Dict[str, Any]] = []
        alerts: List[Dict[str, Any]] = []

        # Briefings
        try:
            meetings = await find_upcoming_meetings(
                context_repo, user.id, within_minutes=120
            )
            for meeting in meetings[:3]:
                try:
                    b = await generate_pre_meeting_briefing(
                        context_repo, user.id, meeting
                    )
                    briefings.append(b)
                except Exception:
                    continue
        except Exception:
            pass

        # Follow-ups
        try:
            followups = await detect_pending_followups(context_repo, user.id)
        except Exception:
            followups = []

        # Relationship alerts (declining relationships)
        try:
            dashboard = await relationship_service.get_relationship_dashboard(
                context_repo, user.id
            )
            alerts = dashboard.get("declining", [])
        except Exception:
            pass

        return {
            "upcoming_briefings": briefings,
            "pending_followups": followups[:10],
            "relationship_alerts": alerts[:5],
            "generated_at": now.isoformat(),
        }

    return router
