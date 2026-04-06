"""Commitment fulfillment detection service.

Detects when open commitments have likely been fulfilled by comparing
them against recent context events using keyword overlap and person
matching.
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from src.infrastructure.repositories.context_event_repository import ContextEventRepository


class CommitmentTracker:
    """Tracks open commitments and detects when they are fulfilled."""

    # Minimum overlap score (0-1) to consider a commitment fulfilled
    FULFILLMENT_THRESHOLD = 0.35

    async def check_fulfillment(
        self, commitment: Any, recent_events: List[Any]
    ) -> Optional[dict]:
        """Check whether *commitment* has been fulfilled by any of *recent_events*.

        The check is based on:
        1. Keyword overlap between commitment content and event content.
        2. Whether the same person is mentioned in both.

        Args:
            commitment: A domain event/object with ``.content`` and
                ``.extracted_people`` attributes.
            recent_events: Recent context events to compare against.

        Returns:
            A fulfillment match dict if score exceeds threshold, else ``None``.
        """
        commitment_text = (getattr(commitment, "content", None) or "").lower()
        commitment_people: Set[str] = set(
            p.lower() for p in (getattr(commitment, "extracted_people", None) or [])
        )
        commitment_keywords = self._extract_keywords(commitment_text)

        if not commitment_keywords:
            return None

        best_match: Optional[dict] = None
        best_score: float = 0.0

        for event in recent_events:
            event_text = (getattr(event, "content", None) or "").lower()
            event_people: Set[str] = set(
                p.lower() for p in (getattr(event, "extracted_people", None) or [])
            )
            event_keywords = self._extract_keywords(event_text)

            if not event_keywords:
                continue

            # Keyword overlap (Jaccard-ish)
            overlap = commitment_keywords & event_keywords
            union = commitment_keywords | event_keywords
            keyword_score = len(overlap) / len(union) if union else 0.0

            # Person overlap bonus
            person_overlap = commitment_people & event_people
            person_bonus = 0.15 if person_overlap else 0.0

            score = keyword_score + person_bonus

            if score > best_score:
                best_score = score
                best_match = {
                    "commitment_id": str(getattr(commitment, "id", "")),
                    "event_id": str(getattr(event, "id", "")),
                    "score": round(score, 3),
                    "overlapping_keywords": list(overlap)[:10],
                    "overlapping_people": list(person_overlap),
                    "event_type": getattr(event, "event_type", ""),
                    "event_content_snippet": event_text[:200],
                }

        if best_match and best_score >= self.FULFILLMENT_THRESHOLD:
            return best_match
        return None

    async def detect_fulfillments(
        self, db: ContextEventRepository, user_id: UUID
    ) -> List[dict]:
        """Scan open commitments against recent events and return fulfillment matches.

        Args:
            db: The context event repository.
            user_id: The user whose commitments to check.

        Returns:
            A list of fulfillment match dicts (one per detected fulfillment).
        """
        now = datetime.utcnow()

        # Load open commitments (last 30 days)
        commitments = await db.query_events(
            user_id=user_id,
            event_types=["commitment"],
            since=now - timedelta(days=30),
            until=now,
            limit=50,
        )

        if not commitments:
            return []

        # Load recent events from the last 48 hours
        recent_events = await db.query_events(
            user_id=user_id,
            event_types=[
                "email_sent",
                "email_received",
                "meeting_transcript",
                "thought",
                "note",
            ],
            since=now - timedelta(hours=48),
            until=now,
            limit=100,
        )

        if not recent_events:
            return []

        fulfillments: List[dict] = []
        for commitment in commitments:
            match = await self.check_fulfillment(commitment, recent_events)
            if match:
                fulfillments.append(match)

        return fulfillments

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_keywords(text: str) -> Set[str]:
        """Extract meaningful keywords from text, filtering stop words."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after", "above",
            "below", "between", "and", "but", "or", "nor", "not", "so",
            "yet", "both", "either", "neither", "each", "every", "all",
            "any", "few", "more", "most", "other", "some", "such", "no",
            "only", "own", "same", "than", "too", "very", "just", "because",
            "if", "when", "where", "how", "what", "which", "who", "whom",
            "this", "that", "these", "those", "i", "me", "my", "we", "our",
            "you", "your", "he", "him", "his", "she", "her", "it", "its",
            "they", "them", "their", "about", "up", "out", "then",
        }
        words = set(re.findall(r"[a-z]{3,}", text))
        return words - stop_words
