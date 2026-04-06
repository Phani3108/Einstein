"""Cross-source entity resolution service.

Resolves mentions like "Phani", "phani.m@corp.com", "@phani" to the same PersonProfile.
"""

from typing import List, Optional
from uuid import UUID
from dataclasses import dataclass

from src.infrastructure.repositories.context_event_repository import ContextEventRepository


@dataclass
class ResolvedPerson:
    person_id: UUID
    name: str
    confidence: float
    match_method: str  # "exact", "alias", "email", "phone", "fuzzy"


class EntityResolutionService:
    def __init__(self, context_repo: ContextEventRepository):
        self._repo = context_repo

    async def resolve_person(self, user_id: UUID, mention: str) -> Optional[ResolvedPerson]:
        """Resolve a text mention to a PersonProfile."""
        mention_clean = mention.strip()
        if not mention_clean:
            return None

        # Strategy 1: Exact name match
        people = await self._repo.get_people(user_id)
        for person in people:
            if person.name.lower() == mention_clean.lower():
                return ResolvedPerson(
                    person_id=person.id,
                    name=person.name,
                    confidence=1.0,
                    match_method="exact",
                )

        # Strategy 2: Alias match
        for person in people:
            aliases = getattr(person, 'aliases', []) or []
            for alias in aliases:
                if alias.lower() == mention_clean.lower():
                    return ResolvedPerson(
                        person_id=person.id,
                        name=person.name,
                        confidence=0.95,
                        match_method="alias",
                    )

        # Strategy 3: Email match
        if "@" in mention_clean:
            for person in people:
                person_email = getattr(person, 'email', '') or ''
                if person_email.lower() == mention_clean.lower():
                    return ResolvedPerson(
                        person_id=person.id,
                        name=person.name,
                        confidence=0.95,
                        match_method="email",
                    )
                # Also check email prefix: phani.m@corp.com matches "phani.m"
                prefix = mention_clean.split("@")[0].lower()
                name_parts = person.name.lower().replace(" ", ".")
                if prefix == name_parts or prefix == person.name.lower().replace(" ", ""):
                    return ResolvedPerson(
                        person_id=person.id,
                        name=person.name,
                        confidence=0.8,
                        match_method="email",
                    )

        # Strategy 4: Phone match (normalize)
        if any(c.isdigit() for c in mention_clean) and len(mention_clean) >= 7:
            normalized = ''.join(c for c in mention_clean if c.isdigit())
            for person in people:
                person_phone = getattr(person, 'phone', '') or ''
                if person_phone:
                    person_normalized = ''.join(c for c in person_phone if c.isdigit())
                    if normalized.endswith(person_normalized[-10:]) and len(person_normalized) >= 7:
                        return ResolvedPerson(
                            person_id=person.id,
                            name=person.name,
                            confidence=0.9,
                            match_method="phone",
                        )

        # Strategy 5: Fuzzy match (Levenshtein distance <= 2)
        for person in people:
            dist = _levenshtein(person.name.lower(), mention_clean.lower())
            if dist <= 2 and len(mention_clean) >= 4:
                return ResolvedPerson(
                    person_id=person.id,
                    name=person.name,
                    confidence=max(0.5, 1.0 - dist * 0.2),
                    match_method="fuzzy",
                )
            # Also check first name match
            first_name = person.name.split()[0].lower() if person.name else ""
            if first_name and first_name == mention_clean.lower() and len(first_name) >= 3:
                return ResolvedPerson(
                    person_id=person.id,
                    name=person.name,
                    confidence=0.7,
                    match_method="fuzzy",
                )

        return None

    async def resolve_people(self, user_id: UUID, mentions: List[str]) -> List[ResolvedPerson]:
        """Resolve multiple mentions, deduplicating by person_id."""
        results = []
        seen_ids = set()
        for mention in mentions:
            resolved = await self.resolve_person(user_id, mention)
            if resolved and resolved.person_id not in seen_ids:
                results.append(resolved)
                seen_ids.add(resolved.person_id)
        return results

    async def learn_alias(self, user_id: UUID, person_id: UUID, alias: str):
        """Add an alias to a PersonProfile for future resolution."""
        from sqlalchemy import text
        db = self._repo._database
        async with db.session() as session:
            # Get current aliases
            result = await session.execute(
                text("SELECT aliases FROM people WHERE id = :pid AND user_id = :uid"),
                {"pid": str(person_id), "uid": str(user_id)},
            )
            row = result.fetchone()
            if not row:
                return

            current_aliases = row[0] or []
            alias_lower = alias.strip().lower()

            # Don't add duplicates
            if alias_lower not in [a.lower() for a in current_aliases]:
                current_aliases.append(alias.strip())
                await session.execute(
                    text("UPDATE people SET aliases = :aliases WHERE id = :pid"),
                    {"aliases": current_aliases, "pid": str(person_id)},
                )
                await session.commit()

    async def auto_learn_from_event(self, user_id: UUID, event: dict):
        """Automatically learn aliases from event structured_data (e.g., email addresses)."""
        sd = event.get("structured_data", {})
        people_mentions = event.get("extracted_people", [])

        # If event has email "from" field, try to link email to a known person
        from_field = sd.get("from", "")
        if from_field and "@" in from_field:
            from email.utils import parseaddr
            name, email_addr = parseaddr(from_field)
            if name and email_addr:
                resolved = await self.resolve_person(user_id, name)
                if resolved:
                    await self.learn_alias(user_id, resolved.person_id, email_addr)


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]
