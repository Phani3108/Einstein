"""Calendar actions — create focus-time blocks and meetings via Google Calendar."""

from datetime import datetime, timedelta
from typing import Any, Dict

import httpx

from .base import BaseAction, ActionRegistry


class BlockFocusTimeAction(BaseAction):
    """Create a Google Calendar event to block focus time."""

    action_type = "block_focus_time"
    provider = "google_calendar"
    requires_confirmation = True

    CALENDAR_API = "https://www.googleapis.com/calendar/v3"

    async def preview(self, params: dict) -> dict:
        """Return proposed event details without creating anything.

        Expected *params* keys:
            - ``title`` (str, optional) — defaults to "Focus Time"
            - ``start`` (str, ISO datetime)
            - ``duration_minutes`` (int, optional) — defaults to 60
            - ``description`` (str, optional)
        """
        title = params.get("title", "Focus Time")
        start = params.get("start", datetime.utcnow().isoformat())
        duration = params.get("duration_minutes", 60)
        description = params.get("description", "Auto-blocked focus time by Einstein")

        try:
            start_dt = datetime.fromisoformat(start)
        except (ValueError, TypeError):
            start_dt = datetime.utcnow()

        end_dt = start_dt + timedelta(minutes=duration)

        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "event": {
                "summary": title,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "description": description,
            },
        }

    async def execute(self, params: dict, credentials: dict) -> dict:
        """Create a focus-time event on Google Calendar."""
        access_token = credentials.get("access_token", "")
        preview = await self.preview(params)
        event_body = preview["event"]

        calendar_event = {
            "summary": event_body["summary"],
            "description": event_body.get("description", ""),
            "start": {"dateTime": event_body["start"], "timeZone": "UTC"},
            "end": {"dateTime": event_body["end"], "timeZone": "UTC"},
            "transparency": "opaque",
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.CALENDAR_API}/calendars/primary/events",
                headers=headers,
                json=calendar_event,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": "created",
            "event_id": data.get("id"),
            "html_link": data.get("htmlLink"),
        }


class CreateMeetingAction(BaseAction):
    """Create a meeting event on Google Calendar."""

    action_type = "create_meeting"
    provider = "google_calendar"
    requires_confirmation = True

    CALENDAR_API = "https://www.googleapis.com/calendar/v3"

    async def preview(self, params: dict) -> dict:
        """Return proposed meeting details.

        Expected *params* keys:
            - ``title`` (str)
            - ``start`` (str, ISO datetime)
            - ``duration_minutes`` (int, optional) — defaults to 30
            - ``attendees`` (list[str]) — email addresses
            - ``description`` (str, optional)
        """
        title = params.get("title", "Meeting")
        start = params.get("start", datetime.utcnow().isoformat())
        duration = params.get("duration_minutes", 30)
        attendees = params.get("attendees", [])
        description = params.get("description", "")

        try:
            start_dt = datetime.fromisoformat(start)
        except (ValueError, TypeError):
            start_dt = datetime.utcnow()

        end_dt = start_dt + timedelta(minutes=duration)

        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "event": {
                "summary": title,
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "attendees": attendees,
                "description": description,
            },
        }

    async def execute(self, params: dict, credentials: dict) -> dict:
        """Create a meeting event on Google Calendar."""
        access_token = credentials.get("access_token", "")
        preview = await self.preview(params)
        event_body = preview["event"]

        calendar_event = {
            "summary": event_body["summary"],
            "description": event_body.get("description", ""),
            "start": {"dateTime": event_body["start"], "timeZone": "UTC"},
            "end": {"dateTime": event_body["end"], "timeZone": "UTC"},
            "attendees": [{"email": e} for e in event_body.get("attendees", [])],
            "conferenceData": {
                "createRequest": {"requestId": f"einstein-{event_body['start']}"}
            },
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.CALENDAR_API}/calendars/primary/events",
                headers=headers,
                json=calendar_event,
                params={"conferenceDataVersion": 1},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": "created",
            "event_id": data.get("id"),
            "html_link": data.get("htmlLink"),
        }


# Register both actions
ActionRegistry.register(BlockFocusTimeAction())
ActionRegistry.register(CreateMeetingAction())
