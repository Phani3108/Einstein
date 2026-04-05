#!/usr/bin/env python
"""Initialize the database with the latest migrations."""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
load_dotenv()


async def init_db() -> None:
    """Initialize the database with the latest migrations."""
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Create database if it doesn't exist
    # This is PostgreSQL specific
    db_name = database_url.split("/")[-1]
    postgres_url = database_url.rsplit("/", 1)[0] + "/postgres"

    engine = create_async_engine(postgres_url)

    try:
        async with engine.begin() as conn:
            # Check if database exists
            result = await conn.execute(
                f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
            )
            exists = result.scalar() is not None

            if not exists:
                print(f"Creating database {db_name}...")
                # Close all connections to the database before dropping
                await conn.execute(f"CREATE DATABASE {db_name}")
                print(f"Database {db_name} created successfully")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        await engine.dispose()

    # Run Alembic migrations
    print("Running database migrations...")
    os.system("alembic upgrade head")
    print("Database migrations completed successfully")


if __name__ == "__main__":
    asyncio.run(init_db())
