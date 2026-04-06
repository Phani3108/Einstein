"""Jira connector — captures issues, comments, and status changes."""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseConnector, ContextEventIn

logger = logging.getLogger(__name__)


class JiraConnector(BaseConnector):
    source_name = "jira"
    auth_type = "oauth2"

    AUTHORIZE_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    SCOPES = ["read:jira-work", "read:jira-user"]

    def _api_base(self, credentials: dict) -> str:
        cloud_id = credentials.get("metadata", {}).get("cloud_id", "")
        return f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3"

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Fetch recently updated Jira issues."""
        import httpx

        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {"Authorization": f"Bearer {access_token}"}
        events: List[ContextEventIn] = []
        api_base = self._api_base(credentials)

        # Calculate minutes since last sync
        since_minutes = max(1, int((datetime.utcnow() - since).total_seconds() / 60))

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{api_base}/search",
                    headers=headers,
                    params={
                        "jql": f"updated >= -{since_minutes}m",
                        "fields": "summary,status,assignee,reporter,comment,priority,project",
                        "maxResults": 50,
                    },
                )
                if resp.status_code != 200:
                    logger.warning("Jira API returned %s: %s", resp.status_code, resp.text[:200])
                    return []

                data = resp.json()
                for issue in data.get("issues", []):
                    event = self._transform_issue(issue, api_base)
                    if event:
                        events.append(event)

            except Exception:
                logger.exception("Error fetching Jira events")

        return events

    def _transform_issue(self, issue: dict, api_base: str) -> Optional[ContextEventIn]:
        """Transform a Jira issue into a ContextEvent."""
        try:
            fields = issue.get("fields", {})
            key = issue.get("key", "")
            summary = fields.get("summary", "")
            status = (fields.get("status") or {}).get("name", "Unknown")
            assignee_obj = fields.get("assignee") or {}
            reporter_obj = fields.get("reporter") or {}
            assignee = assignee_obj.get("displayName", "Unassigned")
            reporter = reporter_obj.get("displayName", "Unknown")
            priority = (fields.get("priority") or {}).get("name", "None")
            project = (fields.get("project") or {}).get("key", "")
            issue_type = (fields.get("issuetype") or {}).get("name", "")

            content = (
                f"Issue {key}: {summary}\n"
                f"Status: {status}\n"
                f"Assignee: {assignee}\n"
                f"Priority: {priority}"
            )

            # Extract people
            people = []
            if assignee and assignee != "Unassigned":
                people.append(assignee)
            if reporter and reporter != "Unknown":
                people.append(reporter)

            # Parse update timestamp
            updated_str = fields.get("updated", "")
            try:
                ts = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.utcnow()

            return ContextEventIn(
                source="jira",
                source_id=issue.get("id"),
                event_type="issue_updated",
                content=content,
                structured_data={
                    "issue_key": key,
                    "project_key": project,
                    "status": status,
                    "assignee": assignee,
                    "reporter": reporter,
                    "priority": priority,
                    "issue_type": issue_type,
                    "url": f"{api_base.split('/rest/')[0]}/browse/{key}",
                },
                timestamp=ts,
                extracted_people=people,
            )
        except Exception:
            logger.exception("Error transforming Jira issue")
            return None

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle Jira webhook payload."""
        webhook_event = payload.get("webhookEvent", "")
        issue = payload.get("issue", {})

        if not issue:
            return []

        # Map Jira webhook events to our event types
        event_type_map = {
            "jira:issue_created": "issue_created",
            "jira:issue_updated": "issue_updated",
            "comment_created": "comment_created",
        }
        event_type = event_type_map.get(webhook_event, "issue_updated")

        fields = issue.get("fields", {})
        key = issue.get("key", "")
        summary = fields.get("summary", "")
        status = (fields.get("status") or {}).get("name", "Unknown")
        assignee_obj = fields.get("assignee") or {}
        reporter_obj = fields.get("reporter") or {}
        assignee = assignee_obj.get("displayName", "Unassigned")
        reporter = reporter_obj.get("displayName", "Unknown")
        priority = (fields.get("priority") or {}).get("name", "None")
        project = (fields.get("project") or {}).get("key", "")
        issue_type = (fields.get("issuetype") or {}).get("name", "")

        content = f"Issue {key}: {summary}\nStatus: {status}\nAssignee: {assignee}\nPriority: {priority}"

        # Add comment text if this is a comment event
        comment = payload.get("comment", {})
        if comment:
            comment_body = comment.get("body", "")
            if isinstance(comment_body, str):
                content += f"\nComment: {comment_body}"

        people = []
        if assignee and assignee != "Unassigned":
            people.append(assignee)
        if reporter and reporter != "Unknown":
            people.append(reporter)

        try:
            ts = datetime.fromisoformat(
                payload.get("timestamp", datetime.utcnow().isoformat()).replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            ts = datetime.utcnow()

        event = ContextEventIn(
            source="jira",
            source_id=issue.get("id"),
            event_type=event_type,
            content=content,
            structured_data={
                "issue_key": key,
                "project_key": project,
                "status": status,
                "assignee": assignee,
                "reporter": reporter,
                "priority": priority,
                "issue_type": issue_type,
                "url": issue.get("self", ""),
            },
            timestamp=ts,
            extracted_people=people,
        )
        return [event]

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify Jira webhook signature using HMAC-SHA256."""
        if not signature or not secret:
            return False
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)


from .registry import ConnectorRegistry
ConnectorRegistry.register(JiraConnector())
