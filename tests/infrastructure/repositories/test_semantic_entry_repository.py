"""Integration tests for the PostgreSQLSemanticEntryRepository."""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import Relationship, SemanticEntry
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.entities.user import User
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import Base
from src.infrastructure.database.models import Thought as ThoughtModel
from src.infrastructure.database.models import User as UserModel
from src.infrastructure.repositories.semantic_entry_repository import (
    PostgreSQLSemanticEntryRepository,
)


@pytest.fixture
def test_db_url():
    """Get the test database URL."""
    return "postgresql+asyncpg://postgres:postgres@localhost/test_semantic_engine"


@pytest_asyncio.fixture
async def db_session(test_db_url):
    """Create a test database session."""
    engine = create_async_engine(test_db_url)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def semantic_entry_repository(test_db_url):
    """Create a test semantic entry repository."""
    database = Database(test_db_url)
    return PostgreSQLSemanticEntryRepository(database)


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user in the database."""
    user_id = uuid.uuid4()
    user = UserModel(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    return User(
        id=user_id,
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest_asyncio.fixture
async def test_thought(db_session, test_user):
    """Create a test thought in the database."""
    thought_id = uuid.uuid4()
    thought = ThoughtModel(
        id=thought_id,
        user_id=test_user.id,
        content="Test thought content",
        timestamp=datetime.now(),
        metadata={},
    )
    db_session.add(thought)
    await db_session.commit()
    return Thought(
        id=thought_id,
        user_id=test_user.id,
        content="Test thought content",
        timestamp=datetime.now(),
        metadata=ThoughtMetadata(),
        semantic_entries=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_semantic_entry(test_thought):
    """Create a sample semantic entry for testing."""
    return SemanticEntry(
        id=uuid.uuid4(),
        thought_id=test_thought.id,
        entity_type=EntityType.PERSON,
        entity_value="John Doe",
        confidence=0.95,
        context="John Doe is a software engineer",
        relationships=[],
        embedding=[0.1, 0.2, 0.3, 0.4],
        extracted_at=datetime.now(),
    )


@pytest.fixture
def sample_semantic_entries(test_thought):
    """Create multiple sample semantic entries for testing."""
    entry1 = SemanticEntry(
        id=uuid.uuid4(),
        thought_id=test_thought.id,
        entity_type=EntityType.PERSON,
        entity_value="John Doe",
        confidence=0.95,
        context="John Doe is a software engineer",
        relationships=[],
        embedding=[0.1, 0.2, 0.3, 0.4],
        extracted_at=datetime.now(),
    )

    entry2 = SemanticEntry(
        id=uuid.uuid4(),
        thought_id=test_thought.id,
        entity_type=EntityType.ORGANIZATION,
        entity_value="Acme Corp",
        confidence=0.85,
        context="Acme Corp is a technology company",
        relationships=[],
        embedding=[0.5, 0.6, 0.7, 0.8],
        extracted_at=datetime.now(),
    )

    return [entry1, entry2]


@pytest.mark.asyncio
async def test_save_semantic_entry(semantic_entry_repository, sample_semantic_entry):
    """Test saving a semantic entry to the repository."""
    # Act
    saved_entry = await semantic_entry_repository.save(sample_semantic_entry)

    # Assert
    assert saved_entry.id == sample_semantic_entry.id
    assert saved_entry.entity_type == sample_semantic_entry.entity_type
    assert saved_entry.entity_value == sample_semantic_entry.entity_value
    assert saved_entry.confidence == sample_semantic_entry.confidence
    assert saved_entry.context == sample_semantic_entry.context
    assert saved_entry.embedding == sample_semantic_entry.embedding


@pytest.mark.asyncio
async def test_save_many_semantic_entries(
    semantic_entry_repository, sample_semantic_entries
):
    """Test saving multiple semantic entries to the repository."""
    # Act
    saved_entries = await semantic_entry_repository.save_many(sample_semantic_entries)

    # Assert
    assert len(saved_entries) == 2
    assert saved_entries[0].id == sample_semantic_entries[0].id
    assert saved_entries[1].id == sample_semantic_entries[1].id
    assert saved_entries[0].entity_value == "John Doe"
    assert saved_entries[1].entity_value == "Acme Corp"


@pytest.mark.asyncio
async def test_find_by_id(semantic_entry_repository, sample_semantic_entry):
    """Test finding a semantic entry by ID."""
    # Arrange
    await semantic_entry_repository.save(sample_semantic_entry)

    # Act
    found_entry = await semantic_entry_repository.find_by_id(sample_semantic_entry.id)

    # Assert
    assert found_entry is not None
    assert found_entry.id == sample_semantic_entry.id
    assert found_entry.entity_type == sample_semantic_entry.entity_type
    assert found_entry.entity_value == sample_semantic_entry.entity_value


@pytest.mark.asyncio
async def test_find_by_thought(
    semantic_entry_repository, sample_semantic_entries, test_thought
):
    """Test finding semantic entries by thought ID."""
    # Arrange
    await semantic_entry_repository.save_many(sample_semantic_entries)

    # Act
    entries = await semantic_entry_repository.find_by_thought(test_thought.id)

    # Assert
    assert len(entries) == 2
    entity_values = [entry.entity_value for entry in entries]
    assert "John Doe" in entity_values
    assert "Acme Corp" in entity_values


@pytest.mark.asyncio
async def test_find_by_entity_type(semantic_entry_repository, sample_semantic_entries):
    """Test finding semantic entries by entity type."""
    # Arrange
    await semantic_entry_repository.save_many(sample_semantic_entries)

    # Act
    person_entries = await semantic_entry_repository.find_by_entity_type(
        EntityType.PERSON
    )
    org_entries = await semantic_entry_repository.find_by_entity_type(
        EntityType.ORGANIZATION
    )

    # Assert
    assert len(person_entries) == 1
    assert person_entries[0].entity_value == "John Doe"

    assert len(org_entries) == 1
    assert org_entries[0].entity_value == "Acme Corp"


@pytest.mark.asyncio
async def test_find_by_entity_value(semantic_entry_repository, sample_semantic_entries):
    """Test finding semantic entries by entity value."""
    # Arrange
    await semantic_entry_repository.save_many(sample_semantic_entries)

    # Act
    john_entries = await semantic_entry_repository.find_by_entity_value("John Doe")
    acme_entries = await semantic_entry_repository.find_by_entity_value("Acme Corp")

    # Assert
    assert len(john_entries) == 1
    assert john_entries[0].entity_type == EntityType.PERSON

    assert len(acme_entries) == 1
    assert acme_entries[0].entity_type == EntityType.ORGANIZATION


@pytest.mark.asyncio
async def test_delete_by_thought(
    semantic_entry_repository, sample_semantic_entries, test_thought
):
    """Test deleting all semantic entries for a thought."""
    # Arrange
    await semantic_entry_repository.save_many(sample_semantic_entries)

    # Act
    await semantic_entry_repository.delete_by_thought(test_thought.id)

    # Assert
    entries = await semantic_entry_repository.find_by_thought(test_thought.id)
    assert len(entries) == 0
