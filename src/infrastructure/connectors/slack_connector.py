"""Slack connector — captures messages from selected channels."""

import hashlib
import hmac
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseConnector, ContextEventIn

logger = logging.getLogger(__name__)


class SlackConnector(BaseConnector):
    source_name = "slack"
    auth_type = "oauth2"

    AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
    TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    API_BASE = "https://slack.com/api"
    SCOPES = [
        "channels:history",
        "channels:read",
        "users:read",
    ]

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Fetch messages from configured Slack channels since last sync."""
        import httpx

        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        events: List[ContextEventIn] = []
        metadata = credentials.get("metadata", {})
        channels = metadata.get("channels", [])
        user_cache: Dict[str, str] = metadata.get("user_cache", {})

        if not channels:
            return []

        since_epoch = str(since.timestamp())

        async with httpx.AsyncClient() as client:
            for channel in channels:
                channel_id = channel.get("id", "") if isinstance(channel, dict) else channel
                channel_name = channel.get("name", channel_id) if isinstance(channel, dict) else channel_id

                try:
                    resp = await client.get(
                        f"{self.API_BASE}/conversations.history",
                        headers=headers,
                        params={
                            "channel": channel_id,
                            "oldest": since_epoch,
                            "limit": 50,
                        },
                    )
                    if resp.status_code != 200:
                        logger.warning("Slack API returned %s for channel %s", resp.status_code, channel_id)
                        continue

                    data = resp.json()
                    if not data.get("ok"):
                        logger.warning("Slack API error for channel %s: %s", channel_id, data.get("error"))
                        continue

                    for msg in data.get("messages", []):
                        if msg.get("subtype") in ("channel_join", "channel_leave", "bot_message"):
                            continue

                        user_id_slack = msg.get("user", "")
                        user_name = await self._resolve_user(
                            client, headers, user_id_slack, user_cache
                        )

                        # Parse timestamp
                        try:
                            ts = datetime.fromtimestamp(float(msg.get("ts", "0")))
                        except (ValueError, TypeError):
                            ts = datetime.utcnow()

                        # Collect reactions
                        reactions = [
                            {"name": r["name"], "count": r["count"]}
                            for r in msg.get("reactions", [])
                        ]

                        event = ContextEventIn(
                            source="slack",
                            source_id=msg.get("ts"),
                            event_type="message",
                            content=msg.get("text", ""),
                            structured_data={
                                "channel_id": channel_id,
                                "channel_name": channel_name,
                                "user_id": user_id_slack,
                                "user_name": user_name,
                                "thread_ts": msg.get("thread_ts"),
                                "reactions": reactions,
                            },
                            timestamp=ts,
                            extracted_people=[user_name] if user_name else [],
                        )
                        events.append(event)

                except Exception:
                    logger.exception("Error fetching Slack messages for channel %s", channel_id)

        return events

    async def _resolve_user(
        self,
        client: Any,
        headers: dict,
        user_id: str,
        cache: Dict[str, str],
    ) -> str:
        """Resolve a Slack user ID to a display name, using cache."""
        if not user_id:
            return ""
        if user_id in cache:
            return cache[user_id]

        try:
            resp = await client.get(
                f"{self.API_BASE}/users.info",
                headers=headers,
                params={"user": user_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    profile = data["user"].get("profile", {})
                    name = profile.get("real_name") or profile.get("display_name") or user_id
                    cache[user_id] = name
                    return name
        except Exception:
            logger.debug("Could not resolve Slack user %s", user_id)

        cache[user_id] = user_id
        return user_id

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle Slack Events API payload."""
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            # Return challenge — caller should send this back as the HTTP response
            return [
                ContextEventIn(
                    source="slack",
                    source_id="url_verification",
                    event_type="url_verification",
                    content=None,
                    structured_data={"challenge": payload["challenge"]},
                    timestamp=datetime.utcnow(),
                )
            ]

        if payload.get("type") != "event_callback":
            return []

        event = payload.get("event", {})
        if event.get("type") != "message":
            return []

        # Skip bot messages and subtypes like edits/deletes
        if event.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
            return []

        user_id = event.get("user", "")

        try:
            ts = datetime.fromtimestamp(float(event.get("ts", "0")))
        except (ValueError, TypeError):
            ts = datetime.utcnow()

        ctx_event = ContextEventIn(
            source="slack",
            source_id=event.get("ts"),
            event_type="message",
            content=event.get("text", ""),
            structured_data={
                "channel_id": event.get("channel", ""),
                "channel_name": "",
                "user_id": user_id,
                "user_name": "",
                "thread_ts": event.get("thread_ts"),
                "reactions": [],
            },
            timestamp=ts,
            extracted_people=[],
        )
        return [ctx_event]

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify Slack signing secret using v0={timestamp}:{body} HMAC-SHA256."""
        if not signature or not secret:
            return False

        # Slack sends signature as v0=<hex_digest> and timestamp in headers
        # The signature param here is expected to be "v0=<hex>" and the timestamp
        # should be prepended to the payload by the caller, but we handle the
        # standard Slack format: sig_basestring = "v0:{timestamp}:{body}"
        # For simplicity, we expect the caller to pass the full signing basestring
        # as payload (v0:{timestamp}:{raw_body}).
        expected = "v0=" + hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


from .registry import ConnectorRegistry
ConnectorRegistry.register(SlackConnector())
