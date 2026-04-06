"""Gmail connector — fetches emails via Gmail API and converts to ContextEvents."""

import base64
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from email.utils import parseaddr

from .base import BaseConnector, ContextEventIn


class GmailConnector(BaseConnector):
    source_name = "gmail"
    auth_type = "oauth2"

    # Google OAuth endpoints
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://gmail.googleapis.com/gmail/v1"
    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

    async def fetch_events(self, user_id: UUID, since: datetime, credentials: dict) -> List[ContextEventIn]:
        """Fetch emails since last sync using Gmail API."""
        import httpx

        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        events = []

        async with httpx.AsyncClient() as client:
            # List messages since last sync
            epoch = int(since.timestamp())
            query = f"after:{epoch}"

            # Respect label filter if configured
            label_filter = credentials.get("metadata", {}).get("labels")
            if label_filter:
                query += f" label:{label_filter}"

            resp = await client.get(
                f"{self.API_BASE}/users/me/messages",
                headers=headers,
                params={"q": query, "maxResults": 50},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            message_ids = [m["id"] for m in data.get("messages", [])]

            # Fetch each message
            for msg_id in message_ids[:50]:  # Cap at 50 per sync
                msg_resp = await client.get(
                    f"{self.API_BASE}/users/me/messages/{msg_id}",
                    headers=headers,
                    params={"format": "metadata", "metadataHeaders": ["From", "To", "Cc", "Subject", "Date"]},
                )
                if msg_resp.status_code != 200:
                    continue

                msg = msg_resp.json()
                event = self._transform_message(msg)
                if event:
                    events.append(event)

        return events

    def _transform_message(self, msg: dict) -> Optional[ContextEventIn]:
        """Transform a Gmail message into a ContextEvent."""
        headers_map = {}
        for h in msg.get("payload", {}).get("headers", []):
            headers_map[h["name"].lower()] = h["value"]

        subject = headers_map.get("subject", "(no subject)")
        from_raw = headers_map.get("from", "")
        to_raw = headers_map.get("to", "")
        cc_raw = headers_map.get("cc", "")
        date_str = headers_map.get("date", "")

        # Parse email addresses
        from_name, from_email = parseaddr(from_raw)
        to_addrs = [parseaddr(a.strip()) for a in to_raw.split(",") if a.strip()]
        cc_addrs = [parseaddr(a.strip()) for a in cc_raw.split(",") if a.strip()]

        # Extract people
        people = []
        if from_name:
            people.append(from_name)
        for name, _ in to_addrs + cc_addrs:
            if name:
                people.append(name)

        # Get snippet as content
        snippet = msg.get("snippet", "")
        content = f"Subject: {subject}\n\n{snippet}"

        # Determine if sent or received (check SENT label)
        labels = msg.get("labelIds", [])
        event_type = "email_sent" if "SENT" in labels else "email_received"

        # Parse timestamp
        try:
            ts = datetime.fromtimestamp(int(msg.get("internalDate", "0")) / 1000)
        except (ValueError, TypeError):
            ts = datetime.now()

        return ContextEventIn(
            source="gmail",
            source_id=msg.get("id"),
            event_type=event_type,
            content=content,
            structured_data={
                "from": from_raw,
                "to": to_raw,
                "cc": cc_raw,
                "subject": subject,
                "thread_id": msg.get("threadId"),
                "labels": labels,
                "has_attachments": any(
                    p.get("filename") for p in msg.get("payload", {}).get("parts", [])
                    if p.get("filename")
                ),
            },
            timestamp=ts,
            extracted_people=people,
        )

    async def handle_webhook(self, payload: dict, headers: dict) -> List[ContextEventIn]:
        """Handle Gmail push notification (Google Pub/Sub)."""
        # Gmail push notifications just tell us there's new mail — we still need to poll
        # This would trigger a fetch_events call
        return []


from .registry import ConnectorRegistry
ConnectorRegistry.register(GmailConnector())
