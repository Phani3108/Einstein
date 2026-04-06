"""Linear connector — captures issues, comments, and project updates."""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseConnector, ContextEventIn

logger = logging.getLogger(__name__)

_LINEAR_ISSUES_QUERY = """
query RecentIssues($since: DateTime!) {
  issues(filter: { updatedAt: { gte: $since } }, first: 50) {
    nodes {
      id
      identifier
      title
      description
      state { name }
      assignee { name }
      creator { name }
      project { name }
      priority
      priorityLabel
      url
      updatedAt
    }
  }
}
"""


class LinearConnector(BaseConnector):
    source_name = "linear"
    auth_type = "oauth2"

    AUTHORIZE_URL = "https://linear.app/oauth/authorize"
    TOKEN_URL = "https://api.linear.app/oauth/token"
    API_URL = "https://api.linear.app/graphql"
    SCOPES = ["read"]

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Fetch recently updated Linear issues via GraphQL API."""
        import httpx

        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {
            "Authorization": access_token,
            "Content-Type": "application/json",
        }
        events: List[ContextEventIn] = []

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    self.API_URL,
                    headers=headers,
                    json={
                        "query": _LINEAR_ISSUES_QUERY,
                        "variables": {"since": since.isoformat() + "Z"},
                    },
                )
                if resp.status_code != 200:
                    logger.warning("Linear API returned %s: %s", resp.status_code, resp.text[:200])
                    return []

                data = resp.json()
                errors = data.get("errors")
                if errors:
                    logger.warning("Linear GraphQL errors: %s", errors)
                    return []

                nodes = data.get("data", {}).get("issues", {}).get("nodes", [])
                for issue in nodes:
                    event = self._transform_issue(issue)
                    if event:
                        events.append(event)

            except Exception:
                logger.exception("Error fetching Linear events")

        return events

    def _transform_issue(self, issue: dict) -> Optional[ContextEventIn]:
        """Transform a Linear issue into a ContextEvent."""
        try:
            identifier = issue.get("identifier", "")
            title = issue.get("title", "")
            description = issue.get("description", "") or ""
            state = (issue.get("state") or {}).get("name", "Unknown")
            assignee = (issue.get("assignee") or {}).get("name", "Unassigned")
            creator = (issue.get("creator") or {}).get("name", "Unknown")
            project = (issue.get("project") or {}).get("name", "")
            priority_label = issue.get("priorityLabel", "None")
            url = issue.get("url", "")

            content = (
                f"Issue {identifier}: {title}\n"
                f"Status: {state}\n"
                f"Assignee: {assignee}\n"
                f"Priority: {priority_label}"
            )
            if description:
                content += f"\n{description[:200]}"

            people = []
            if assignee and assignee != "Unassigned":
                people.append(assignee)
            if creator and creator != "Unknown" and creator != assignee:
                people.append(creator)

            # Parse timestamp
            updated_str = issue.get("updatedAt", "")
            try:
                ts = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                ts = datetime.utcnow()

            return ContextEventIn(
                source="linear",
                source_id=issue.get("id"),
                event_type="issue_updated",
                content=content,
                structured_data={
                    "issue_id": issue.get("id"),
                    "identifier": identifier,
                    "title": title,
                    "state": state,
                    "assignee": assignee,
                    "creator": creator,
                    "project": project,
                    "priority": issue.get("priority"),
                    "priority_label": priority_label,
                    "url": url,
                },
                timestamp=ts,
                extracted_people=people,
            )
        except Exception:
            logger.exception("Error transforming Linear issue")
            return None

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle Linear webhook payload."""
        action = payload.get("action", "")  # create, update, remove
        data_type = payload.get("type", "")  # Issue, Comment, Project
        data = payload.get("data", {})

        if not data:
            return []

        # Map action + type to event_type
        event_type_map = {
            ("create", "Issue"): "issue_created",
            ("update", "Issue"): "issue_updated",
            ("remove", "Issue"): "issue_removed",
            ("create", "Comment"): "comment_created",
            ("update", "Comment"): "comment_updated",
            ("create", "Project"): "project_created",
            ("update", "Project"): "project_updated",
        }
        event_type = event_type_map.get((action, data_type), f"{data_type.lower()}_{action}")

        # Build content based on type
        content = ""
        people = []
        structured: Dict[str, Any] = {
            "action": action,
            "type": data_type,
        }

        if data_type == "Issue":
            identifier = data.get("identifier", "")
            title = data.get("title", "")
            state = (data.get("state") or {}).get("name", "Unknown")
            assignee = (data.get("assignee") or {}).get("name", "Unassigned")
            content = f"Issue {identifier}: {title}\nStatus: {state}\nAssignee: {assignee}"
            structured.update({
                "issue_id": data.get("id"),
                "identifier": identifier,
                "title": title,
                "state": state,
                "assignee": assignee,
                "url": data.get("url", ""),
            })
            if assignee and assignee != "Unassigned":
                people.append(assignee)

        elif data_type == "Comment":
            body = (data.get("body", "") or "")[:200]
            issue = data.get("issue", {})
            content = f"Comment on {issue.get('identifier', '')}: {body}"
            structured.update({
                "comment_id": data.get("id"),
                "issue_identifier": issue.get("identifier", ""),
                "url": data.get("url", ""),
            })
            user = data.get("user", {})
            if user.get("name"):
                people.append(user["name"])

        elif data_type == "Project":
            name = data.get("name", "")
            content = f"Project {action}: {name}"
            structured.update({
                "project_id": data.get("id"),
                "project_name": name,
                "url": data.get("url", ""),
            })

        try:
            ts_str = data.get("updatedAt") or data.get("createdAt", "")
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = datetime.utcnow()

        event = ContextEventIn(
            source="linear",
            source_id=data.get("id"),
            event_type=event_type,
            content=content,
            structured_data=structured,
            timestamp=ts,
            extracted_people=people,
        )
        return [event]

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify Linear webhook signature using HMAC-SHA256."""
        if not signature or not secret:
            return False
        expected = hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


from .registry import ConnectorRegistry
ConnectorRegistry.register(LinearConnector())
