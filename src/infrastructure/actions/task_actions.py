"""Task actions — create Jira tickets and Linear issues."""

from typing import Any, Dict

import httpx

from .base import BaseAction, ActionRegistry


class CreateJiraTicketAction(BaseAction):
    """Create a Jira issue via the Jira REST API."""

    action_type = "create_jira_ticket"
    provider = "jira"
    requires_confirmation = True

    async def preview(self, params: dict) -> dict:
        """Return proposed Jira issue details.

        Expected *params* keys:
            - ``project_key`` (str) — e.g. "ENG"
            - ``summary`` (str) — issue title
            - ``description`` (str, optional)
            - ``issue_type`` (str, optional) — defaults to "Task"
            - ``priority`` (str, optional) — defaults to "Medium"
            - ``assignee`` (str, optional) — account ID
        """
        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "issue": {
                "project_key": params.get("project_key", ""),
                "summary": params.get("summary", ""),
                "description": params.get("description", ""),
                "issue_type": params.get("issue_type", "Task"),
                "priority": params.get("priority", "Medium"),
                "assignee": params.get("assignee"),
            },
        }

    async def execute(self, params: dict, credentials: dict) -> dict:
        """Create an issue in Jira.

        *credentials* should contain:
            - ``base_url`` — Jira site URL (e.g. ``https://mysite.atlassian.net``)
            - ``email`` — Jira account email
            - ``api_token`` — Jira API token
        """
        base_url = credentials.get("base_url", "").rstrip("/")
        email = credentials.get("email", "")
        api_token = credentials.get("api_token", "")

        preview = await self.preview(params)
        issue_info = preview["issue"]

        issue_payload = {
            "fields": {
                "project": {"key": issue_info["project_key"]},
                "summary": issue_info["summary"],
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": issue_info.get("description", ""),
                                }
                            ],
                        }
                    ],
                },
                "issuetype": {"name": issue_info["issue_type"]},
                "priority": {"name": issue_info["priority"]},
            }
        }

        if issue_info.get("assignee"):
            issue_payload["fields"]["assignee"] = {"accountId": issue_info["assignee"]}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base_url}/rest/api/3/issue",
                auth=(email, api_token),
                json=issue_payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "status": "created",
            "issue_id": data.get("id"),
            "issue_key": data.get("key"),
            "url": f"{base_url}/browse/{data.get('key', '')}",
        }


class CreateLinearIssueAction(BaseAction):
    """Create an issue in Linear via the GraphQL API."""

    action_type = "create_linear_issue"
    provider = "linear"
    requires_confirmation = True

    LINEAR_API = "https://api.linear.app/graphql"

    async def preview(self, params: dict) -> dict:
        """Return proposed Linear issue details.

        Expected *params* keys:
            - ``team_id`` (str) — Linear team ID
            - ``title`` (str)
            - ``description`` (str, optional)
            - ``priority`` (int, optional) — 0=none, 1=urgent, 2=high, 3=medium, 4=low
            - ``assignee_id`` (str, optional)
        """
        return {
            "action_type": self.action_type,
            "provider": self.provider,
            "issue": {
                "team_id": params.get("team_id", ""),
                "title": params.get("title", ""),
                "description": params.get("description", ""),
                "priority": params.get("priority", 0),
                "assignee_id": params.get("assignee_id"),
            },
        }

    async def execute(self, params: dict, credentials: dict) -> dict:
        """Create an issue in Linear.

        *credentials* should contain:
            - ``api_key`` — Linear API key
        """
        api_key = credentials.get("api_key", "")
        preview = await self.preview(params)
        issue_info = preview["issue"]

        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    url
                }
            }
        }
        """

        variables: dict = {
            "input": {
                "teamId": issue_info["team_id"],
                "title": issue_info["title"],
                "description": issue_info.get("description", ""),
                "priority": issue_info.get("priority", 0),
            }
        }

        if issue_info.get("assignee_id"):
            variables["input"]["assigneeId"] = issue_info["assignee_id"]

        headers = {"Authorization": api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.LINEAR_API,
                headers=headers,
                json={"query": mutation, "variables": variables},
            )
            resp.raise_for_status()
            data = resp.json()

        issue_data = (
            data.get("data", {}).get("issueCreate", {}).get("issue", {})
        )
        return {
            "status": "created",
            "issue_id": issue_data.get("id"),
            "identifier": issue_data.get("identifier"),
            "url": issue_data.get("url"),
        }


# Register both actions
ActionRegistry.register(CreateJiraTicketAction())
ActionRegistry.register(CreateLinearIssueAction())
