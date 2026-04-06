"""Zoom connector — fetches meeting recordings/transcripts via Zoom API."""

import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from .base import BaseConnector, ContextEventIn


class ZoomConnector(BaseConnector):
    """Connector for Zoom — pulls past meeting recordings and handles
    the ``recording.completed`` webhook event."""

    source_name = "zoom"
    auth_type = "oauth2"

    # Zoom OAuth / API endpoints
    AUTHORIZE_URL = "https://zoom.us/oauth/authorize"
    TOKEN_URL = "https://zoom.us/oauth/token"
    API_BASE = "https://api.zoom.us/v2"
    SCOPES = ["meeting:read"]

    # ------------------------------------------------------------------
    # Poll-based sync
    # ------------------------------------------------------------------

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """List past meetings and fetch their recordings/transcripts."""
        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        events: List[ContextEventIn] = []

        async with httpx.AsyncClient(timeout=30) as client:
            # List past meetings for the authed user
            from_date = since.strftime("%Y-%m-%d")
            to_date = datetime.utcnow().strftime("%Y-%m-%d")

            resp = await client.get(
                f"{self.API_BASE}/users/me/recordings",
                headers=headers,
                params={"from": from_date, "to": to_date, "page_size": 50},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            meetings = data.get("meetings", [])

            for meeting in meetings:
                event = self._transform_meeting(meeting)
                if event:
                    events.append(event)

        return events

    # ------------------------------------------------------------------
    # Webhook handling
    # ------------------------------------------------------------------

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle ``recording.completed`` webhook from Zoom.

        Returns a list containing a single ContextEvent with the meeting
        transcript download URL embedded in ``structured_data``.
        """
        event_type = payload.get("event", "")
        if event_type != "recording.completed":
            return []

        meeting_payload = payload.get("payload", {}).get("object", {})
        event = self._transform_meeting(meeting_payload)
        return [event] if event else []

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify Zoom webhook signature using the webhook secret token.

        Zoom sends an ``x-zm-signature`` header computed as
        ``v0=HMAC-SHA256(secret, timestamp.payload)``.  The *signature*
        parameter should be the full header value and *secret* the app's
        webhook secret token.
        """
        if not secret or not signature:
            return False

        # Zoom also sends a timestamp header — extract from signature prefix
        try:
            # signature format: "v0=<hex>"
            expected_prefix = "v0="
            if not signature.startswith(expected_prefix):
                return False

            provided_hash = signature[len(expected_prefix):]
            computed = hmac.new(
                secret.encode(), payload, hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(computed, provided_hash)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transform_meeting(self, meeting: dict) -> Optional[ContextEventIn]:
        """Transform a Zoom meeting/recording object into a ContextEvent."""
        topic = meeting.get("topic", "Untitled Meeting")
        meeting_id = str(meeting.get("uuid") or meeting.get("id", ""))

        # Parse start time
        start_str = meeting.get("start_time", "")
        try:
            ts = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = datetime.utcnow()

        # Collect recording files — look for transcript or chat files
        recording_files = meeting.get("recording_files", [])
        transcript_url: Optional[str] = None
        transcript_content: Optional[str] = None

        for rf in recording_files:
            file_type = rf.get("file_type", "").upper()
            if file_type == "TRANSCRIPT":
                transcript_url = rf.get("download_url")
            elif file_type == "CHAT":
                transcript_url = transcript_url or rf.get("download_url")

        # Extract attendees / participants as people
        participants = meeting.get("participants", [])
        people: List[str] = []
        for p in participants:
            name = p.get("name") or p.get("user_name", "")
            if name:
                people.append(name)

        # Also pull from host
        host_email = meeting.get("host_email", "")
        if host_email:
            people.append(host_email)

        content = f"Meeting: {topic}"
        if transcript_content:
            content += f"\n\n{transcript_content}"

        return ContextEventIn(
            source="zoom",
            source_id=meeting_id,
            event_type="meeting_transcript",
            content=content,
            structured_data={
                "topic": topic,
                "meeting_id": meeting_id,
                "duration": meeting.get("duration"),
                "host_email": host_email,
                "transcript_download_url": transcript_url,
                "recording_count": len(recording_files),
            },
            timestamp=ts,
            extracted_people=people,
        )


# Register with the global ConnectorRegistry
from .registry import ConnectorRegistry

ConnectorRegistry.register(ZoomConnector())
