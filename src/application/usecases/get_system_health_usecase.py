"""Get system health use case for admin functionality."""

from datetime import datetime
from typing import Dict, Any

from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.thought_repository import ThoughtRepository
from src.infrastructure.database.connection import Database


class GetSystemHealthUseCase:
    """Use case for retrieving system health information."""

    def __init__(
        self,
        database: Database,
        user_repository: UserRepository,
        thought_repository: ThoughtRepository,
    ):
        """Initialize the use case.

        Args:
            database: Database connection for health checks
            user_repository: Repository for user data access
            thought_repository: Repository for thought data access
        """
        self._database = database
        self._user_repository = user_repository
        self._thought_repository = thought_repository

    async def execute(self) -> Dict[str, Any]:
        """Execute the get system health use case.

        Returns:
            Dictionary containing system health information

        Raises:
            RepositoryError: If database operation fails
        """
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "services": {},
            "statistics": {},
        }

        try:
            # Check database connectivity
            async with self._database.session() as session:
                # Simple query to test database connection
                await session.execute("SELECT 1")
                health_data["services"]["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful",
                }
        except Exception as e:
            health_data["services"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
            }
            health_data["status"] = "degraded"

        try:
            # Get basic statistics - just test repository accessibility
            users = await self._user_repository.find_all(limit=1)  # Just to test connection
            # For thoughts, we'll use a dummy UUID to test the method without actual data
            from uuid import uuid4
            dummy_user_id = uuid4()
            thoughts = await self._thought_repository.find_by_user(
                user_id=dummy_user_id, skip=0, limit=1  # This will return empty but tests connection
            )
            
            health_data["statistics"] = {
                "users_accessible": True,
                "thoughts_accessible": True,
            }
        except Exception as e:
            health_data["statistics"] = {
                "error": f"Failed to retrieve statistics: {str(e)}",
            }
            health_data["status"] = "degraded"

        return health_data