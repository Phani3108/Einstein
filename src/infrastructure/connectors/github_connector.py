"""GitHub connector — captures PRs, issues, and code review comments."""

import hashlib
import hmac
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .base import BaseConnector, ContextEventIn

logger = logging.getLogger(__name__)

# Map GitHub event types to our event types
_GITHUB_EVENT_TYPE_MAP = {
    "PushEvent": "push",
    "PullRequestEvent": "pr_opened",
    "IssuesEvent": "issue_created",
    "IssueCommentEvent": "issue_comment",
    "PullRequestReviewEvent": "review_submitted",
}

_RELEVANT_EVENT_TYPES = set(_GITHUB_EVENT_TYPE_MAP.keys())


class GitHubConnector(BaseConnector):
    source_name = "github"
    auth_type = "oauth2"

    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_BASE = "https://api.github.com"
    SCOPES = ["repo", "read:user"]

    async def fetch_events(
        self, user_id: UUID, since: datetime, credentials: dict
    ) -> List[ContextEventIn]:
        """Fetch recent GitHub activity for the authenticated user."""
        import httpx

        access_token = credentials.get("access_token")
        if not access_token:
            return []

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }
        events: List[ContextEventIn] = []
        username = credentials.get("metadata", {}).get("username", "")

        async with httpx.AsyncClient() as client:
            try:
                # If username isn't cached, fetch it
                if not username:
                    user_resp = await client.get(
                        f"{self.API_BASE}/user", headers=headers
                    )
                    if user_resp.status_code == 200:
                        username = user_resp.json().get("login", "")

                if not username:
                    logger.warning("Could not determine GitHub username")
                    return []

                resp = await client.get(
                    f"{self.API_BASE}/users/{username}/events",
                    headers=headers,
                    params={"per_page": 50},
                )
                if resp.status_code != 200:
                    logger.warning("GitHub API returned %s: %s", resp.status_code, resp.text[:200])
                    return []

                for gh_event in resp.json():
                    # Filter by date
                    created = gh_event.get("created_at", "")
                    try:
                        ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        ts = datetime.utcnow()

                    if ts < since:
                        continue

                    event_type_raw = gh_event.get("type", "")
                    if event_type_raw not in _RELEVANT_EVENT_TYPES:
                        continue

                    event = self._transform_event(gh_event, ts)
                    if event:
                        events.append(event)

            except Exception:
                logger.exception("Error fetching GitHub events")

        return events

    def _transform_event(
        self, gh_event: dict, ts: datetime
    ) -> Optional[ContextEventIn]:
        """Transform a GitHub event into a ContextEvent."""
        try:
            event_type_raw = gh_event.get("type", "")
            payload = gh_event.get("payload", {})
            repo = gh_event.get("repo", {}).get("name", "")
            actor = gh_event.get("actor", {}).get("login", "")
            action = payload.get("action", "")

            # Refine event type based on action
            event_type = _GITHUB_EVENT_TYPE_MAP.get(event_type_raw, "activity")
            if event_type_raw == "PullRequestEvent" and action:
                event_type = f"pr_{action}"
            elif event_type_raw == "IssuesEvent" and action:
                event_type = f"issue_{action}"

            # Build content and structured data based on event type
            content = ""
            structured = {
                "repo": repo,
                "action": action,
                "author": actor,
            }
            people = [actor]

            if event_type_raw == "PushEvent":
                commits = payload.get("commits", [])
                size = payload.get("size", len(commits))
                ref = payload.get("ref", "").replace("refs/heads/", "")
                messages = [c.get("message", "").split("\n")[0] for c in commits[:5]]
                content = f"Pushed {size} commit(s) to {repo}/{ref}:\n" + "\n".join(
                    f"  - {m}" for m in messages
                )
                structured["number"] = None
                structured["title"] = None
                structured["url"] = None

            elif event_type_raw == "PullRequestEvent":
                pr = payload.get("pull_request", {})
                title = pr.get("title", "")
                number = pr.get("number", 0)
                url = pr.get("html_url", "")
                content = f"PR #{number} {action}: {title} in {repo}"
                structured["number"] = number
                structured["title"] = title
                structured["url"] = url
                # Add assignees
                for a in pr.get("assignees", []):
                    login = a.get("login", "")
                    if login and login != actor:
                        people.append(login)

            elif event_type_raw == "IssuesEvent":
                issue = payload.get("issue", {})
                title = issue.get("title", "")
                number = issue.get("number", 0)
                url = issue.get("html_url", "")
                content = f"Issue #{number} {action}: {title} in {repo}"
                structured["number"] = number
                structured["title"] = title
                structured["url"] = url
                for a in issue.get("assignees", []):
                    login = a.get("login", "")
                    if login and login != actor:
                        people.append(login)

            elif event_type_raw == "IssueCommentEvent":
                issue = payload.get("issue", {})
                comment = payload.get("comment", {})
                number = issue.get("number", 0)
                title = issue.get("title", "")
                url = comment.get("html_url", "")
                body = (comment.get("body", "") or "")[:200]
                content = f"Comment on #{number} ({title}) in {repo}: {body}"
                structured["number"] = number
                structured["title"] = title
                structured["url"] = url

            elif event_type_raw == "PullRequestReviewEvent":
                pr = payload.get("pull_request", {})
                review = payload.get("review", {})
                number = pr.get("number", 0)
                title = pr.get("title", "")
                state = review.get("state", "")
                url = review.get("html_url", "")
                content = f"Review {state} on PR #{number} ({title}) in {repo}"
                structured["number"] = number
                structured["title"] = title
                structured["url"] = url

            return ContextEventIn(
                source="github",
                source_id=gh_event.get("id"),
                event_type=event_type,
                content=content,
                structured_data=structured,
                timestamp=ts,
                extracted_people=people,
            )
        except Exception:
            logger.exception("Error transforming GitHub event")
            return None

    async def handle_webhook(
        self, payload: dict, headers: dict
    ) -> List[ContextEventIn]:
        """Handle GitHub webhook payload. X-GitHub-Event header determines the type."""
        gh_event_type = headers.get("x-github-event", headers.get("X-GitHub-Event", ""))

        handler_map = {
            "pull_request": self._handle_pr_webhook,
            "issues": self._handle_issue_webhook,
            "issue_comment": self._handle_comment_webhook,
            "pull_request_review": self._handle_review_webhook,
        }

        handler = handler_map.get(gh_event_type)
        if not handler:
            return []

        event = handler(payload)
        return [event] if event else []

    def _handle_pr_webhook(self, payload: dict) -> Optional[ContextEventIn]:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "")
        number = pr.get("number", 0)
        title = pr.get("title", "")
        url = pr.get("html_url", "")
        author = pr.get("user", {}).get("login", "")

        people = [author]
        for a in pr.get("assignees", []):
            login = a.get("login", "")
            if login and login != author:
                people.append(login)

        return ContextEventIn(
            source="github",
            source_id=str(pr.get("id", "")),
            event_type=f"pr_{action}",
            content=f"PR #{number} {action}: {title} in {repo}",
            structured_data={"repo": repo, "action": action, "number": number, "title": title, "url": url, "author": author},
            timestamp=datetime.utcnow(),
            extracted_people=people,
        )

    def _handle_issue_webhook(self, payload: dict) -> Optional[ContextEventIn]:
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        repo = payload.get("repository", {}).get("full_name", "")
        number = issue.get("number", 0)
        title = issue.get("title", "")
        url = issue.get("html_url", "")
        author = issue.get("user", {}).get("login", "")

        people = [author]
        for a in issue.get("assignees", []):
            login = a.get("login", "")
            if login and login != author:
                people.append(login)

        return ContextEventIn(
            source="github",
            source_id=str(issue.get("id", "")),
            event_type=f"issue_{action}",
            content=f"Issue #{number} {action}: {title} in {repo}",
            structured_data={"repo": repo, "action": action, "number": number, "title": title, "url": url, "author": author},
            timestamp=datetime.utcnow(),
            extracted_people=people,
        )

    def _handle_comment_webhook(self, payload: dict) -> Optional[ContextEventIn]:
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        comment = payload.get("comment", {})
        repo = payload.get("repository", {}).get("full_name", "")
        number = issue.get("number", 0)
        title = issue.get("title", "")
        url = comment.get("html_url", "")
        author = comment.get("user", {}).get("login", "")
        body = (comment.get("body", "") or "")[:200]

        return ContextEventIn(
            source="github",
            source_id=str(comment.get("id", "")),
            event_type="issue_comment",
            content=f"Comment on #{number} ({title}) in {repo}: {body}",
            structured_data={"repo": repo, "action": action, "number": number, "title": title, "url": url, "author": author},
            timestamp=datetime.utcnow(),
            extracted_people=[author],
        )

    def _handle_review_webhook(self, payload: dict) -> Optional[ContextEventIn]:
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        review = payload.get("review", {})
        repo = payload.get("repository", {}).get("full_name", "")
        number = pr.get("number", 0)
        title = pr.get("title", "")
        state = review.get("state", "")
        url = review.get("html_url", "")
        author = review.get("user", {}).get("login", "")

        return ContextEventIn(
            source="github",
            source_id=str(review.get("id", "")),
            event_type="review_submitted",
            content=f"Review {state} on PR #{number} ({title}) in {repo}",
            structured_data={"repo": repo, "action": action, "number": number, "title": title, "url": url, "author": author},
            timestamp=datetime.utcnow(),
            extracted_people=[author],
        )

    def verify_webhook(
        self, payload: bytes, signature: str, secret: str
    ) -> bool:
        """Verify GitHub webhook signature using HMAC-SHA256 (X-Hub-Signature-256)."""
        if not signature or not secret:
            return False
        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


from .registry import ConnectorRegistry
ConnectorRegistry.register(GitHubConnector())
