"""Relationship health scoring service.

Provides comprehensive relationship strength scoring based on recency,
frequency, diversity, and reciprocity of interactions.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.infrastructure.repositories.context_event_repository import ContextEventRepository

logger = logging.getLogger(__name__)


class RelationshipHealthService:
    """Computes relationship health scores for people in a user's network.

    Scoring components (each 0-25 pts, total 0-100):
        - Recency:     Days since last interaction
        - Frequency:   Interactions per week over 90 days
        - Diversity:   Number of different channels used
        - Reciprocity: Balance between sent vs received
    """

    # Grade thresholds
    STRONG_THRESHOLD = 75
    MODERATE_THRESHOLD = 50
    WEAK_THRESHOLD = 25

    async def compute_relationship_score(
        self,
        db: ContextEventRepository,
        user_id: UUID,
        person_id: UUID,
    ) -> Dict[str, Any]:
        """Compute a detailed relationship health score for one person.

        Args:
            db: The context event repository.
            user_id: The user whose perspective to score from.
            person_id: The person to score.

        Returns:
            A relationship score dict with components, grade, and trend.
        """
        now = datetime.utcnow()

        # Resolve person name
        person_name = await self._resolve_person_name(db, user_id, person_id)

        # Gather all interactions with this person over the last 90 days
        interactions = await self._get_person_interactions(
            db, user_id, person_name, now, days=90
        )

        # Also gather the prior 30-day window (days 60-90 before the last 30)
        # for trend calculation
        prior_interactions = await self._get_person_interactions(
            db, user_id, person_name, now, days=90, offset_days=30
        )

        # Compute components
        recency_score = self._compute_recency(interactions, now)
        frequency_score = self._compute_frequency(interactions)
        diversity_score = self._compute_diversity(interactions)
        reciprocity_score = self._compute_reciprocity(interactions)

        total_score = recency_score + frequency_score + diversity_score + reciprocity_score
        grade = self._score_to_grade(total_score)

        # Interaction counts
        count_30d = sum(
            1 for ev in interactions
            if (now - getattr(ev, "timestamp", now)).days <= 30
        )
        count_90d = len(interactions)

        # Last interaction
        last_interaction: Optional[str] = None
        if interactions:
            sorted_interactions = sorted(
                interactions,
                key=lambda e: getattr(e, "timestamp", now),
                reverse=True,
            )
            last_interaction = getattr(
                sorted_interactions[0], "timestamp", now
            ).isoformat()

        # Primary channel
        primary_channel = self._get_primary_channel(interactions)

        # Trend: compare last 30d vs prior 30d
        recent_count = count_30d
        prior_count = sum(
            1 for ev in interactions
            if 30 < (now - getattr(ev, "timestamp", now)).days <= 60
        )
        trend = self._compute_trend(recent_count, prior_count)

        return {
            "person_id": str(person_id),
            "person_name": person_name,
            "score": total_score,
            "grade": grade,
            "components": {
                "recency": recency_score,
                "frequency": frequency_score,
                "diversity": diversity_score,
                "reciprocity": reciprocity_score,
            },
            "last_interaction": last_interaction,
            "interaction_count_30d": count_30d,
            "interaction_count_90d": count_90d,
            "primary_channel": primary_channel,
            "trend": trend,
        }

    async def compute_all_relationships(
        self,
        db: ContextEventRepository,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Compute relationship scores for all known people.

        Args:
            db: The context event repository.
            user_id: The user.

        Returns:
            A list of relationship score dicts, sorted by score descending.
        """
        try:
            people = await db.get_people(user_id)
        except Exception as exc:
            logger.warning("Failed to get people for user %s: %s", user_id, exc)
            return []

        scores: List[Dict[str, Any]] = []
        for person in (people or []):
            try:
                score = await self.compute_relationship_score(
                    db, user_id, person.id
                )
                scores.append(score)
            except Exception as exc:
                logger.warning(
                    "Failed to score relationship with %s: %s",
                    getattr(person, "name", "unknown"),
                    exc,
                )

        scores.sort(key=lambda s: s["score"], reverse=True)
        return scores

    async def get_relationship_dashboard(
        self,
        db: ContextEventRepository,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Generate a relationship health dashboard.

        Provides summary statistics, top relationships, those needing
        attention, and dormant contacts.

        Args:
            db: The context event repository.
            user_id: The user.

        Returns:
            A dashboard dict with summary, top, declining, improving,
            and dormant relationship lists.
        """
        all_scores = await self.compute_all_relationships(db, user_id)

        # Summary counts
        strong = sum(1 for s in all_scores if s["grade"] == "strong")
        moderate = sum(1 for s in all_scores if s["grade"] == "moderate")
        weak = sum(1 for s in all_scores if s["grade"] == "weak")
        dormant = sum(1 for s in all_scores if s["grade"] == "dormant")

        # Top 10 strongest
        top_10 = all_scores[:10]

        # Declining (need attention) — those with trend "declining"
        declining = [s for s in all_scores if s["trend"] == "declining"][:5]

        # Improving
        improving = [s for s in all_scores if s["trend"] == "improving"][:5]

        # Dormant (not contacted in 30+ days)
        now = datetime.utcnow()
        dormant_list: List[Dict[str, Any]] = []
        for s in all_scores:
            last = s.get("last_interaction")
            if last:
                try:
                    last_dt = datetime.fromisoformat(last)
                    if (now - last_dt).days >= 30:
                        dormant_list.append(s)
                except (ValueError, TypeError):
                    pass
            elif s["interaction_count_90d"] == 0:
                dormant_list.append(s)

        return {
            "summary": {
                "total_contacts": len(all_scores),
                "strong": strong,
                "moderate": moderate,
                "weak": weak,
                "dormant": dormant,
            },
            "top_relationships": top_10,
            "declining": declining,
            "improving": improving,
            "dormant": dormant_list[:10],
        }

    # ------------------------------------------------------------------
    # Scoring components
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_recency(interactions: list, now: datetime) -> int:
        """Recency score (0-25): based on days since last interaction."""
        if not interactions:
            return 0

        most_recent = max(
            (getattr(ev, "timestamp", now) for ev in interactions),
            default=now,
        )
        days = (now - most_recent).days

        if days <= 0:
            return 25
        elif days <= 7:
            return 20
        elif days <= 14:
            return 15
        elif days <= 30:
            return 10
        elif days <= 60:
            return 5
        else:
            return 0

    @staticmethod
    def _compute_frequency(interactions: list) -> int:
        """Frequency score (0-25): interactions per week over 90 days."""
        count = len(interactions)
        weeks = 13  # 90 days ~ 13 weeks
        per_week = count / weeks if weeks > 0 else 0

        if per_week >= 5:
            return 25
        elif per_week >= 3:
            return 20
        elif per_week >= 1.5:
            return 15
        elif per_week >= 0.5:
            return 10
        elif per_week > 0:
            return 5
        else:
            return 0

    @staticmethod
    def _compute_diversity(interactions: list) -> int:
        """Diversity score (0-25): number of unique channels used."""
        channels = set()
        for ev in interactions:
            source = getattr(ev, "source", None)
            if source:
                channels.add(source.lower())
            etype = getattr(ev, "event_type", None)
            if etype:
                # Normalize event types to channel categories
                if "email" in etype:
                    channels.add("email")
                elif "slack" in etype or "message" in etype:
                    channels.add("messaging")
                elif "meeting" in etype or "calendar" in etype:
                    channels.add("meeting")
                elif "call" in etype or "phone" in etype:
                    channels.add("call")

        num_channels = len(channels)
        if num_channels >= 4:
            return 25
        elif num_channels >= 3:
            return 20
        elif num_channels >= 2:
            return 15
        elif num_channels >= 1:
            return 10
        else:
            return 0

    @staticmethod
    def _compute_reciprocity(interactions: list) -> int:
        """Reciprocity score (0-25): balance between sent vs received."""
        sent = 0
        received = 0

        for ev in interactions:
            etype = getattr(ev, "event_type", "")
            sd = getattr(ev, "structured_data", None) or {}
            direction = sd.get("direction", "")

            if "sent" in etype or direction == "outbound":
                sent += 1
            elif "received" in etype or direction == "inbound":
                received += 1

        total = sent + received
        if total == 0:
            return 0

        # Perfect balance = 0.5, skewed = closer to 0 or 1
        ratio = min(sent, received) / max(sent, received) if max(sent, received) > 0 else 0
        # ratio of 1.0 (balanced) = 25 pts, 0.0 (one-sided) = 0 pts
        return round(ratio * 25)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_grade(score: int) -> str:
        """Map total score to a grade label."""
        if score >= 75:
            return "strong"
        elif score >= 50:
            return "moderate"
        elif score >= 25:
            return "weak"
        else:
            return "dormant"

    @staticmethod
    def _compute_trend(recent_count: int, prior_count: int) -> str:
        """Determine trend by comparing recent vs prior period counts."""
        if recent_count > prior_count and recent_count >= 2:
            return "improving"
        elif prior_count > recent_count and prior_count >= 2:
            return "declining"
        else:
            return "stable"

    @staticmethod
    def _get_primary_channel(interactions: list) -> str:
        """Determine the most-used communication channel."""
        from collections import Counter
        channels: List[str] = []
        for ev in interactions:
            source = getattr(ev, "source", None) or getattr(ev, "event_type", "unknown")
            channels.append(source)

        if not channels:
            return "unknown"
        return Counter(channels).most_common(1)[0][0]

    @staticmethod
    async def _resolve_person_name(
        db: ContextEventRepository,
        user_id: UUID,
        person_id: UUID,
    ) -> str:
        """Resolve a person_id to a display name."""
        try:
            people = await db.get_people(user_id)
            for p in (people or []):
                if p.id == person_id:
                    return p.name
        except Exception:
            pass
        return str(person_id)

    @staticmethod
    async def _get_person_interactions(
        db: ContextEventRepository,
        user_id: UUID,
        person_name: str,
        now: datetime,
        days: int = 90,
        offset_days: int = 0,
    ) -> list:
        """Get interactions involving a person within a time window.

        Args:
            db: The context event repository.
            user_id: The user.
            person_name: Name of the person to filter by.
            now: Current timestamp.
            days: How many days back to look.
            offset_days: Shift the window back by this many days.

        Returns:
            List of matching context events.
        """
        since = now - timedelta(days=days + offset_days)
        until = now - timedelta(days=offset_days)

        try:
            events = await db.query_events(
                user_id=user_id,
                event_types=[
                    "email_received", "email_sent",
                    "meeting_transcript", "calendar_event",
                    "slack_message", "message",
                    "call", "phone_call",
                ],
                since=since,
                until=until,
                limit=500,
            )
        except Exception:
            return []

        # Filter to events mentioning this person
        matched = []
        person_lower = person_name.lower()
        for ev in (events or []):
            ev_people = [
                p.lower()
                for p in (getattr(ev, "extracted_people", None) or [])
            ]
            if person_lower in ev_people:
                matched.append(ev)

        return matched
