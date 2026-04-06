"""Outlook connector — fetches emails via Microsoft Graph API and converts to ContextEvents."""

from datetime import datetime
from email.utils import parseaddr
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from .base import BaseConnector, ContextEventIn


class OutlookConnector(BaseConnector):
    """Connector for Microsoft Outlook / Office 365 mail via Microsoft Graph.

    Uses OAuth 2.0 with delegated (user) permissions.  The caller is
    responsible for token refresh; this connector expects a valid
    ``access_token`` in the credentials dict.
    """

    source_name = "outlook"
    auth_type = "oauth2"

    # Microsoft identity platform endpoints
    AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2/token"
    API_BASE = "https://graph.microsoft.com/v1.0"
    SCOPES = ["Mail.Read"]

    # Fields to request from the messages endpoint.
    _SELECT_FIELDS = (
        "id,subject,from,toRecipients,ccRecipients,"
        "bodyPreview,receivedDateTime,conversationId,hasAttachments"
    )

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Fetch emails received since *since* via Microsoft Graph.

        Uses ``$filter`` on ``receivedDateTime`` and ``$select`` to keep
        payloads small.
        """
        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        events: List[ContextEventIn] = []

        since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/me/messages",
                headers=headers,
                params={
                    "$filter": f"receivedDateTime ge {since_iso}",
                    "$select": self._SELECT_FIELDS,
                    "$orderby": "receivedDateTime desc",
                    "$top": "50",
                },
                timeout=30.0,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            messages = data.get("value", [])

            for msg in messages:
                event = self._transform_message(msg)
                if event:
                    events.append(event)

        return events

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle a Microsoft Graph change notification.

        Graph subscriptions send a validation request on creation (which the
        API layer must handle) and then change notifications.  Each notification
        contains a ``resource`` path (e.g. ``me/messages/{id}``) but *not* the
        full message — a follow-up fetch is required.

        This method extracts the resource IDs so the caller can trigger
        ``fetch_events`` or fetch individual messages.
        """
        # Graph change notifications arrive in a "value" array.
        notifications = payload.get("value", [])
        resource_ids: List[str] = []
        for notification in notifications:
            resource = notification.get("resource", "")
            # resource looks like "me/messages/{id}"
            if "/messages/" in resource:
                msg_id = resource.split("/messages/")[-1]
                resource_ids.append(msg_id)

        # Change notifications don't carry the message body, so we return
        # empty events here.  The orchestrator should call fetch_events or
        # fetch individual messages using the resource IDs.
        # We store the IDs in a synthetic event for the caller.
        if resource_ids:
            return [
                ContextEventIn(
                    source="outlook",
                    source_id=None,
                    event_type="webhook_notification",
                    content=None,
                    structured_data={"resource_ids": resource_ids},
                    timestamp=datetime.utcnow(),
                )
            ]
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transform_message(self, msg: dict) -> Optional[ContextEventIn]:
        """Transform a Microsoft Graph message object into a ContextEvent."""
        subject = msg.get("subject", "(no subject)")

        # From
        from_obj = msg.get("from", {}).get("emailAddress", {})
        from_name = from_obj.get("name", "")
        from_email = from_obj.get("address", "")
        from_raw = f"{from_name} <{from_email}>" if from_name else from_email

        # To
        to_list = msg.get("toRecipients", [])
        to_raw = ", ".join(
            _format_recipient(r) for r in to_list
        )

        # CC
        cc_list = msg.get("ccRecipients", [])
        cc_raw = ", ".join(
            _format_recipient(r) for r in cc_list
        )

        # Snippet / preview
        snippet = msg.get("bodyPreview", "")
        content = f"Subject: {subject}\n\n{snippet}"

        # Timestamp
        received = msg.get("receivedDateTime", "")
        try:
            ts = datetime.fromisoformat(received.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = datetime.utcnow()

        # Extract people names
        people: List[str] = []
        if from_name:
            people.append(from_name)
        for r in to_list + cc_list:
            name = r.get("emailAddress", {}).get("name", "")
            if name:
                people.append(name)

        return ContextEventIn(
            source="outlook",
            source_id=msg.get("id"),
            event_type="email_received",
            content=content,
            structured_data={
                "from": from_raw,
                "to": to_raw,
                "cc": cc_raw,
                "subject": subject,
                "thread_id": msg.get("conversationId"),
                "has_attachments": msg.get("hasAttachments", False),
            },
            timestamp=ts,
            extracted_people=people,
        )


def _format_recipient(recipient: dict) -> str:
    """Format a Graph ``emailAddress`` recipient as ``Name <email>``."""
    addr = recipient.get("emailAddress", {})
    name = addr.get("name", "")
    email = addr.get("address", "")
    if name:
        return f"{name} <{email}>"
    return email


# Register with the connector registry on import.
from .registry import ConnectorRegistry

ConnectorRegistry.register(OutlookConnector())
