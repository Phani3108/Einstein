"""Telegram connector — fetches messages via Telegram Bot API and converts to ContextEvents."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx

from .base import BaseConnector, ContextEventIn


class TelegramConnector(BaseConnector):
    """Connector for Telegram using the Bot API.

    Supports two ingestion modes:
    1. **Polling** via `fetch_events()` — calls `getUpdates` with an offset cursor.
    2. **Webhook** via `handle_webhook()` — accepts Telegram webhook payloads pushed
       to our endpoint.
    """

    source_name = "telegram"
    auth_type = "bot_token"

    API_BASE = "https://api.telegram.org/bot{token}"

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Poll Telegram for new messages using getUpdates.

        The sync cursor (``offset``) is stored in ``credentials["metadata"]["offset"]``.
        After processing, the caller should persist the updated offset so subsequent
        calls only return new updates.
        """
        bot_token = credentials.get("bot_token") or credentials.get("api_key")
        if not bot_token:
            return []

        base_url = self.API_BASE.format(token=bot_token)
        offset = credentials.get("metadata", {}).get("offset")

        params: Dict[str, Any] = {"timeout": 0, "allowed_updates": '["message"]'}
        if offset is not None:
            params["offset"] = offset

        events: List[ContextEventIn] = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{base_url}/getUpdates",
                params=params,
                timeout=30.0,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not data.get("ok"):
                return []

            updates = data.get("result", [])
            for update in updates:
                message = update.get("message")
                if message is None:
                    continue

                event = self._transform_message(message)
                if event:
                    events.append(event)

                # Advance offset past this update.
                new_offset = update["update_id"] + 1
                credentials.setdefault("metadata", {})["offset"] = new_offset

        return events

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle an inbound Telegram webhook payload.

        Telegram sends a single ``Update`` object per request.
        """
        message = payload.get("message")
        if message is None:
            return []

        event = self._transform_message(message)
        return [event] if event else []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transform_message(self, message: dict) -> Optional[ContextEventIn]:
        """Transform a Telegram message object into a ContextEvent."""
        text = message.get("text")
        if not text:
            # Skip non-text messages (stickers, photos, etc.) for now.
            return None

        # Sender info
        sender = message.get("from", {})
        sender_name = _format_user_name(sender)

        # Chat info (group title or private)
        chat = message.get("chat", {})
        chat_title = chat.get("title")  # None for private chats
        chat_type = chat.get("type", "private")

        # Forwarded message info
        forward_origin = message.get("forward_origin") or {}
        forwarded_from: Optional[str] = None
        if forward_origin:
            fwd_sender = forward_origin.get("sender_user")
            if fwd_sender:
                forwarded_from = _format_user_name(fwd_sender)
            elif forward_origin.get("sender_user_name"):
                forwarded_from = forward_origin["sender_user_name"]
            elif forward_origin.get("chat"):
                forwarded_from = forward_origin["chat"].get("title")
        # Legacy field fallback
        if not forwarded_from and message.get("forward_from"):
            forwarded_from = _format_user_name(message["forward_from"])

        # Build content
        content_parts = []
        if forwarded_from:
            content_parts.append(f"[Forwarded from {forwarded_from}]")
        content_parts.append(text)
        content = "\n".join(content_parts)

        # Timestamp
        ts = datetime.fromtimestamp(
            message.get("date", 0), tz=timezone.utc
        )

        # Extracted people
        people: List[str] = []
        if sender_name:
            people.append(sender_name)
        if forwarded_from:
            people.append(forwarded_from)

        structured: Dict[str, Any] = {
            "chat_id": chat.get("id"),
            "chat_type": chat_type,
            "message_id": message.get("message_id"),
        }
        if chat_title:
            structured["chat_title"] = chat_title
        if forwarded_from:
            structured["forwarded_from"] = forwarded_from

        return ContextEventIn(
            source="telegram",
            source_id=str(message.get("message_id", "")),
            event_type="message_received",
            content=content,
            structured_data=structured,
            timestamp=ts,
            extracted_people=people,
        )


def _format_user_name(user: dict) -> str:
    """Build a display name from a Telegram User object."""
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    full = f"{first} {last}".strip()
    return full or user.get("username", "Unknown")


# Register with the connector registry on import.
from .registry import ConnectorRegistry

ConnectorRegistry.register(TelegramConnector())
