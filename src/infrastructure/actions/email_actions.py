"""Email actions — create Gmail drafts."""

import base64
from email.mime.text import MIMEText
from typing import Any, Dict, List

import httpx

from .base import BaseAction, ActionRegistry


class DraftEmailAction(BaseAction):
    """Create a draft email in Gmail."""

    action_type = "draft_email"
    provider = "gmail"
    requires_confirmation = True

    GMAIL_API = "https://gmail.googleapis.com/gmail/v1"

    async def preview(self, params: dict) -> dict:
        """Return proposed draft details.

        Expected *params* keys:
            - ``to`` (list[str]) — recipient email addresses
            - ``subject`` (str)
            - ``body`` (str)
            - ``cc`` (list[str], optional)
        """
        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "draft": {
                "to": params.get("to", []),
                "cc": params.get("cc", []),
                "subject": params.get("subject", ""),
                "body": params.get("body", ""),
            },
        }

    async def execute(self, params: dict, credentials: dict) -> dict:
        """Create a draft in the user's Gmail account."""
        access_token = credentials.get("access_token", "")
        preview = await self.preview(params)
        draft_info = preview["draft"]

        # Build the MIME message
        msg = MIMEText(draft_info["body"])
        msg["To"] = ", ".join(draft_info["to"])
        msg["Subject"] = draft_info["subject"]
        if draft_info.get("cc"):
            msg["Cc"] = ", ".join(draft_info["cc"])

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.GMAIL_API}/users/me/drafts",
                headers=headers,
                json={"message": {"raw": raw}},
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": "created",
            "draft_id": data.get("id"),
            "message_id": data.get("message", {}).get("id"),
        }


# Register action
ActionRegistry.register(DraftEmailAction())
