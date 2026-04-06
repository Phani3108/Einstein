"""Action management API routes.

Endpoints for previewing, executing, and listing outbound actions
(e.g. block focus time, draft email, create Jira ticket).
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.actions.base import ActionRegistry
from src.domain.entities.user import User


# ---- Request / Response Models ----

class ActionPreviewRequest(BaseModel):
    action_type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ActionExecuteRequest(BaseModel):
    action_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class ActionPreviewResponse(BaseModel):
    action_type: str
    provider: str
    preview: Dict[str, Any]
    requires_confirmation: bool


class ActionExecuteResponse(BaseModel):
    action_type: str
    status: str
    result: Dict[str, Any]


class SuggestedAction(BaseModel):
    action_type: str
    provider: str
    title: str
    reason: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ActionHistoryItem(BaseModel):
    action_type: str
    provider: str
    status: str
    executed_at: datetime
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)


# In-memory action log (replace with DB persistence in production)
_action_history: List[Dict[str, Any]] = []


# ---- Router Factory ----

def create_actions_router(
    context_repo: ContextEventRepository,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    """Create the actions router with injected dependencies."""

    router = APIRouter(prefix="/api/v1/actions", tags=["actions"])

    # Ensure action modules are imported so they self-register
    import src.infrastructure.actions.calendar_actions  # noqa: F401
    import src.infrastructure.actions.email_actions  # noqa: F401
    import src.infrastructure.actions.task_actions  # noqa: F401

    # ---- Suggested actions ----

    @router.get("/suggested", response_model=List[SuggestedAction])
    async def suggested_actions(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Return AI-suggested actions based on recent context.

        Examines recent commitments, dormant contacts, and upcoming meetings
        to propose helpful outbound actions.
        """
        suggestions: List[SuggestedAction] = []
        now = datetime.utcnow()

        # 1. Commitments due soon — suggest creating a reminder / task
        try:
            commitments = await context_repo.query_events(
                user_id=user.id,
                event_types=["commitment"],
                since=now - timedelta(days=7),
                until=now + timedelta(days=1),
                limit=10,
            )
            for c in commitments:
                suggestions.append(
                    SuggestedAction(
                        action_type="create_jira_ticket",
                        provider="jira",
                        title=f"Follow up: {(c.content or '')[:60]}",
                        reason="Commitment due within 24 hours",
                        params={
                            "summary": c.content or "Follow-up task",
                            "description": f"Auto-suggested from commitment: {c.content}",
                        },
                    )
                )
        except Exception:
            pass

        # 2. Dormant people — suggest reaching out
        try:
            dormant = await context_repo.query_events(
                user_id=user.id,
                event_types=["email_received", "email_sent", "meeting_transcript"],
                since=now - timedelta(days=60),
                until=now - timedelta(days=25),
                limit=10,
            )
            seen_people: set = set()
            for ev in dormant:
                for person in (ev.extracted_people or []):
                    if person not in seen_people:
                        seen_people.add(person)
                        suggestions.append(
                            SuggestedAction(
                                action_type="draft_email",
                                provider="gmail",
                                title=f"Reconnect with {person}",
                                reason="No interaction in ~30 days",
                                params={
                                    "to": [],
                                    "subject": f"Catching up — {person}",
                                    "body": f"Hi {person},\n\nJust wanted to check in. Hope you're doing well!\n\nBest",
                                },
                            )
                        )
        except Exception:
            pass

        # 3. Upcoming meetings — suggest blocking prep time
        try:
            upcoming = await context_repo.query_events(
                user_id=user.id,
                event_types=["calendar_event"],
                since=now,
                until=now + timedelta(hours=4),
                limit=5,
            )
            for ev in upcoming:
                suggestions.append(
                    SuggestedAction(
                        action_type="block_focus_time",
                        provider="google_calendar",
                        title=f"Prep for: {(ev.content or 'Meeting')[:40]}",
                        reason="Upcoming meeting — block prep time",
                        params={
                            "title": f"Prep: {(ev.content or 'Meeting')[:40]}",
                            "duration_minutes": 15,
                        },
                    )
                )
        except Exception:
            pass

        return suggestions

    # ---- Preview an action ----

    @router.post("/preview", response_model=ActionPreviewResponse)
    async def preview_action(
        req: ActionPreviewRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Preview what an action will do before executing it."""
        action = ActionRegistry.get(req.action_type)
        if not action:
            raise HTTPException(404, f"Unknown action type: {req.action_type}")

        preview_data = await action.preview(req.params)
        return ActionPreviewResponse(
            action_type=action.action_type,
            provider=action.provider,
            preview=preview_data,
            requires_confirmation=action.requires_confirmation,
        )

    # ---- Execute an action ----

    @router.post("/execute", response_model=ActionExecuteResponse)
    async def execute_action(
        req: ActionExecuteRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Execute a confirmed action."""
        action = ActionRegistry.get(req.action_type)
        if not action:
            raise HTTPException(404, f"Unknown action type: {req.action_type}")

        # Fetch credentials for the provider
        creds = await context_repo.get_integration_credential(
            user.id, action.provider
        )
        if not creds or not creds.get("is_active"):
            raise HTTPException(
                400,
                f"No active {action.provider} integration. Connect it first.",
            )

        try:
            result = await action.execute(req.params, creds)
        except Exception as exc:
            raise HTTPException(502, f"Action execution failed: {exc}")

        # Log the action
        _action_history.append(
            {
                "action_type": action.action_type,
                "provider": action.provider,
                "status": result.get("status", "completed"),
                "executed_at": datetime.utcnow().isoformat(),
                "params": req.params,
                "result": result,
                "user_id": str(user.id),
            }
        )

        return ActionExecuteResponse(
            action_type=action.action_type,
            status=result.get("status", "completed"),
            result=result,
        )

    # ---- Action history ----

    @router.get("/history", response_model=List[ActionHistoryItem])
    async def action_history(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Return past action execution log for the current user."""
        user_history = [
            h for h in _action_history if h.get("user_id") == str(user.id)
        ]
        return [
            ActionHistoryItem(
                action_type=h["action_type"],
                provider=h["provider"],
                status=h["status"],
                executed_at=datetime.fromisoformat(h["executed_at"]),
                params=h.get("params", {}),
                result=h.get("result", {}),
            )
            for h in user_history
        ]

    return router
