"""PostgreSQL implementation of the ThoughtRepository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.thought import Thought
from src.domain.exceptions import ThoughtNotFoundError
from src.domain.repositories.thought_repository import ThoughtRepository
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import Thought as ThoughtModel


class PostgreSQLThoughtRepository(ThoughtRepository):
    """PostgreSQL implementation of the ThoughtRepository."""

    def __init__(self, database: Database):
        """Initialize the repository.

        Args:
            database: The database connection manager
        """
        self._database = database

    async def save(self, thought: Thought) -> Thought:
        """Save a thought to the repository.

        Args:
            thought: The thought to save

        Returns:
            The saved thought with any generated fields populated
        """
        db_thought = ThoughtModel.from_domain(thought)

        async with self._database.session() as session:
            session.add(db_thought)
            await session.commit()
            await session.refresh(db_thought)
            return db_thought.to_domain()

    async def find_by_id(self, thought_id: UUID) -> Optional[Thought]:
        """Find a thought by its ID.

        Args:
            thought_id: The ID of the thought to find

        Returns:
            The thought if found, None otherwise
        """
        async with self._database.session() as session:
            stmt = select(ThoughtModel).where(ThoughtModel.id == thought_id)
            result = await session.execute(stmt)
            db_thought = result.scalar_one_or_none()

            if db_thought is None:
                return None

            return db_thought.to_domain()

    async def find_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Thought]:
        """Find thoughts by user ID.

        Args:
            user_id: The ID of the user whose thoughts to find
            skip: Number of thoughts to skip for pagination
            limit: Maximum number of thoughts to return

        Returns:
            A list of thoughts belonging to the user
        """
        async with self._database.session() as session:
            stmt = (
                select(ThoughtModel)
                .where(ThoughtModel.user_id == user_id)
                .order_by(ThoughtModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            db_thoughts = result.scalars().all()

            return [db_thought.to_domain() for db_thought in db_thoughts]

    async def update(self, thought: Thought) -> Thought:
        """Update a thought in the repository.

        Args:
            thought: The thought to update

        Returns:
            The updated thought

        Raises:
            ThoughtNotFoundError: If the thought does not exist
        """
        async with self._database.session() as session:
            stmt = select(ThoughtModel).where(ThoughtModel.id == thought.id)
            result = await session.execute(stmt)
            db_thought = result.scalar_one_or_none()

            if db_thought is None:
                raise ThoughtNotFoundError(thought.id)

            # Update fields from domain object
            updated_thought = ThoughtModel.from_domain(thought)
            db_thought.content = updated_thought.content
            db_thought.timestamp = updated_thought.timestamp
            db_thought.thought_metadata = updated_thought.thought_metadata
            db_thought.updated_at = updated_thought.updated_at

            await session.commit()
            await session.refresh(db_thought)
            return db_thought.to_domain()

    async def delete(self, thought_id: UUID) -> None:
        """Delete a thought from the repository.

        Args:
            thought_id: The ID of the thought to delete

        Raises:
            ThoughtNotFoundError: If the thought does not exist
        """
        async with self._database.session() as session:
            stmt = select(ThoughtModel).where(ThoughtModel.id == thought_id)
            result = await session.execute(stmt)
            db_thought = result.scalar_one_or_none()

            if db_thought is None:
                raise ThoughtNotFoundError(thought_id)

            await session.delete(db_thought)
            await session.commit()