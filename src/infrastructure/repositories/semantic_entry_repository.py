"""PostgreSQL implementation of the SemanticEntryRepository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.repositories.semantic_entry_repository import SemanticEntryRepository
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import SemanticEntry as SemanticEntryModel


class PostgreSQLSemanticEntryRepository(SemanticEntryRepository):
    """PostgreSQL implementation of the SemanticEntryRepository."""

    def __init__(self, database: Database):
        """Initialize the repository.

        Args:
            database: The database connection manager
        """
        self._database = database

    async def save(self, semantic_entry: SemanticEntry) -> SemanticEntry:
        """Save a semantic entry to the repository.

        Args:
            semantic_entry: The semantic entry to save

        Returns:
            The saved semantic entry with any generated fields populated
        """
        db_entry = SemanticEntryModel.from_domain(semantic_entry)

        async with self._database.session() as session:
            session.add(db_entry)
            await session.commit()
            await session.refresh(db_entry)
            return db_entry.to_domain()

    async def save_many(
        self, semantic_entries: List[SemanticEntry]
    ) -> List[SemanticEntry]:
        """Save multiple semantic entries to the repository.

        Args:
            semantic_entries: The semantic entries to save

        Returns:
            The saved semantic entries with any generated fields populated
        """
        db_entries = [
            SemanticEntryModel.from_domain(entry) for entry in semantic_entries
        ]

        async with self._database.session() as session:
            session.add_all(db_entries)
            await session.commit()

            # Refresh all entries to get generated fields
            for db_entry in db_entries:
                await session.refresh(db_entry)

            return [db_entry.to_domain() for db_entry in db_entries]

    async def find_by_id(self, entry_id: UUID) -> Optional[SemanticEntry]:
        """Find a semantic entry by its ID.

        Args:
            entry_id: The ID of the semantic entry to find

        Returns:
            The semantic entry if found, None otherwise
        """
        async with self._database.session() as session:
            stmt = (
                select(SemanticEntryModel)
                .options(selectinload(SemanticEntryModel.relationships))
                .where(SemanticEntryModel.id == entry_id)
            )
            result = await session.execute(stmt)
            db_entry = result.scalar_one_or_none()

            if db_entry is None:
                return None

            return db_entry.to_domain()

    async def find_by_thought(self, thought_id: UUID) -> List[SemanticEntry]:
        """Find semantic entries by thought ID.

        Args:
            thought_id: The ID of the thought whose semantic entries to find

        Returns:
            A list of semantic entries belonging to the thought
        """
        async with self._database.session() as session:
            stmt = (
                select(SemanticEntryModel)
                .options(selectinload(SemanticEntryModel.relationships))
                .where(SemanticEntryModel.thought_id == thought_id)
                .order_by(SemanticEntryModel.extracted_at.desc())
            )
            result = await session.execute(stmt)
            db_entries = result.scalars().all()

            return [db_entry.to_domain() for db_entry in db_entries]

    async def find_by_entity_type(
        self, entity_type: EntityType, skip: int = 0, limit: int = 100
    ) -> List[SemanticEntry]:
        """Find semantic entries by entity type.

        Args:
            entity_type: The type of entity to find
            skip: Number of entries to skip for pagination
            limit: Maximum number of entries to return

        Returns:
            A list of semantic entries of the specified type
        """
        async with self._database.session() as session:
            stmt = (
                select(SemanticEntryModel)
                .options(selectinload(SemanticEntryModel.relationships))
                .where(SemanticEntryModel.entity_type == entity_type.value)
                .order_by(SemanticEntryModel.extracted_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            db_entries = result.scalars().all()

            return [db_entry.to_domain() for db_entry in db_entries]

    async def find_by_entity_value(
        self, entity_value: str, skip: int = 0, limit: int = 100
    ) -> List[SemanticEntry]:
        """Find semantic entries by entity value.

        Args:
            entity_value: The value of the entity to find
            skip: Number of entries to skip for pagination
            limit: Maximum number of entries to return

        Returns:
            A list of semantic entries with the specified value
        """
        async with self._database.session() as session:
            stmt = (
                select(SemanticEntryModel)
                .options(selectinload(SemanticEntryModel.relationships))
                .where(SemanticEntryModel.entity_value == entity_value)
                .order_by(SemanticEntryModel.extracted_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            db_entries = result.scalars().all()

            return [db_entry.to_domain() for db_entry in db_entries]

    async def delete_by_thought(self, thought_id: UUID) -> None:
        """Delete all semantic entries for a thought.

        Args:
            thought_id: The ID of the thought whose semantic entries to delete
        """
        async with self._database.session() as session:
            stmt = select(SemanticEntryModel).where(
                SemanticEntryModel.thought_id == thought_id
            )
            result = await session.execute(stmt)
            db_entries = result.scalars().all()

            for db_entry in db_entries:
                await session.delete(db_entry)

            await session.commit()
