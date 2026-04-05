"""PostgreSQL implementation of the UserRepository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.exceptions import UserNotFoundError
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import User as UserModel


class PostgreSQLUserRepository(UserRepository):
    """PostgreSQL implementation of the UserRepository."""

    def __init__(self, database: Database):
        """Initialize the repository.

        Args:
            database: The database connection manager
        """
        self._database = database

    async def save(self, user: User) -> User:
        """Save a user to the repository.

        Args:
            user: The user to save

        Returns:
            The saved user with any generated fields populated
        """
        db_user = UserModel.from_domain(user)

        async with self._database.session() as session:
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
            return db_user.to_domain()

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find a user by their ID.

        Args:
            user_id: The ID of the user to find

        Returns:
            The user if found, None otherwise
        """
        async with self._database.session() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            if db_user is None:
                return None

            return db_user.to_domain()

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find a user by their email.

        Args:
            email: The email of the user to find

        Returns:
            The user if found, None otherwise
        """
        async with self._database.session() as session:
            stmt = select(UserModel).where(UserModel.email == email)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            if db_user is None:
                return None

            return db_user.to_domain()

    async def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Find all users.

        Args:
            skip: Number of users to skip for pagination
            limit: Maximum number of users to return

        Returns:
            A list of users
        """
        async with self._database.session() as session:
            stmt = (
                select(UserModel)
                .order_by(UserModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await session.execute(stmt)
            db_users = result.scalars().all()

            return [db_user.to_domain() for db_user in db_users]

    async def update(self, user: User) -> User:
        """Update a user in the repository.

        Args:
            user: The user to update

        Returns:
            The updated user

        Raises:
            UserNotFoundError: If the user does not exist
        """
        async with self._database.session() as session:
            stmt = select(UserModel).where(UserModel.id == user.id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            if db_user is None:
                raise UserNotFoundError(user.id)

            # Update fields from domain object
            updated_user = UserModel.from_domain(user)
            db_user.email = updated_user.email
            db_user.hashed_password = updated_user.hashed_password
            db_user.is_active = updated_user.is_active
            db_user.is_admin = updated_user.is_admin
            db_user.updated_at = updated_user.updated_at
            db_user.last_login = updated_user.last_login

            await session.commit()
            await session.refresh(db_user)
            return db_user.to_domain()

    async def delete(self, user_id: UUID) -> None:
        """Delete a user from the repository.

        Args:
            user_id: The ID of the user to delete

        Raises:
            UserNotFoundError: If the user does not exist
        """
        async with self._database.session() as session:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            if db_user is None:
                raise UserNotFoundError(user_id)

            await session.delete(db_user)
            await session.commit()
