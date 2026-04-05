---
inclusion: always
---

# Clean Architecture Principles

This document defines the core architectural principles for the Personal Semantic Engine (Einstein) project. All code must adhere to these principles to maintain clean, testable, and maintainable architecture.

## Core Principles

### 1. Pure Domain Entities and Interfaces

- **Domain objects** are the only communication mechanism between layers
- All entities must be pure Python classes with Pydantic validation
- Interfaces must be defined using Python Abstract Base Classes (ABC)
- No external dependencies in domain layer (no SQLAlchemy, FastAPI, etc.)

```python
# ✅ Good - Pure domain entity
from pydantic import BaseModel
from abc import ABC, abstractmethod

class Thought(BaseModel):
    id: str
    content: str
    user_id: str
    timestamp: datetime

class ThoughtRepository(ABC):
    @abstractmethod
    async def save(self, thought: Thought) -> Thought:
        pass
```

### 2. Cross-Layer Communication

- **Only domain objects** can be passed between layers
- No DTOs, database models, or API models in cross-layer communication
- Each layer converts to/from domain objects at its boundaries

```python
# ✅ Good - UseCase receives and returns domain objects
class CreateThoughtUseCase:
    def __init__(self, repo: ThoughtRepository):
        self._repo = repo
    
    async def execute(self, thought: Thought) -> Thought:
        return await self._repo.save(thought)

# ❌ Bad - UseCase dealing with database models
class CreateThoughtUseCase:
    async def execute(self, db_model: SQLAlchemyThought) -> dict:
        # Wrong - should use domain objects
```

### 3. Repository Layer Rules

- Repository interfaces must NOT import any datasource implementations
- Repository interfaces must NOT import DTOs or database models
- Repository implementations handle conversion to/from database models
- Repository interfaces only work with domain objects

```python
# ✅ Good - Repository interface
from abc import ABC, abstractmethod
from domain.entities import Thought

class ThoughtRepository(ABC):
    @abstractmethod
    async def save(self, thought: Thought) -> Thought:
        pass

# ✅ Good - Repository implementation
from infrastructure.database.models import ThoughtModel

class PostgreSQLThoughtRepository(ThoughtRepository):
    async def save(self, thought: Thought) -> Thought:
        db_model = ThoughtModel.from_domain(thought)
        # Database operations
        return db_model.to_domain()
```

### 4. UseCase Layer Rules

- UseCase interfaces must NOT import datasource/repository implementations
- UseCase interfaces must NOT import DTOs or database models
- UseCases orchestrate business logic using domain objects
- UseCases are injected with repository interfaces, not implementations

```python
# ✅ Good - UseCase with interface dependency
class CreateThoughtUseCase:
    def __init__(self, thought_repo: ThoughtRepository, 
                 entity_extractor: EntityExtractionService):
        self._thought_repo = thought_repo
        self._entity_extractor = entity_extractor

# ❌ Bad - UseCase with concrete dependency
class CreateThoughtUseCase:
    def __init__(self, postgres_repo: PostgreSQLThoughtRepository):
        # Wrong - should depend on interface
```

### 5. Dependency Flow Direction

Dependencies must always flow downwards:
```
UI Layer → UseCase Layer → Repository Layer → DataSource Layer
```

- Higher layers depend on lower layer interfaces
- Lower layers never import from higher layers
- Dependency injection provides concrete implementations

### 6. Dependency Injection Rules

- All implementations injected via DI container
- No direct instantiation of concrete classes across layers
- Interfaces define contracts, DI provides implementations

```python
# ✅ Good - DI configuration
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    # Infrastructure
    thought_repo = providers.Factory(PostgreSQLThoughtRepository)
    
    # Application
    create_thought_usecase = providers.Factory(
        CreateThoughtUseCase,
        thought_repo=thought_repo
    )
```

### 7. Stateless Components

- Repository implementations must be stateless
- UseCase implementations must be stateless  
- UI code must be stateless
- State managed only in domain entities and database

### 8. UI Layer Rules

- UI must be free of business logic
- UI loosely coupled with UseCases
- UI must NOT import lower layers (repository, datasource)
- All business logic handled in UseCase layer

```python
# ✅ Good - UI delegates to UseCase
class ThoughtController:
    def __init__(self, create_usecase: CreateThoughtUseCase):
        self._create_usecase = create_usecase
    
    async def create_thought(self, request: CreateThoughtRequest):
        thought = Thought.from_request(request)
        result = await self._create_usecase.execute(thought)
        return ThoughtResponse.from_domain(result)
```

### 9. CLI-First Development

- Build simple CLI to test UseCases before production UI
- CLI validates UseCase layer works independently of web framework
- Production UI built after UseCase layer is proven

## Architecture Validation

### Layer Import Rules

```python
# Domain Layer - NO external imports
# ✅ Can import: typing, datetime, enum, pydantic, abc
# ❌ Cannot import: sqlalchemy, fastapi, requests, etc.

# Application Layer (UseCases)
# ✅ Can import: domain layer, typing, abc
# ❌ Cannot import: infrastructure, presentation layers

# Infrastructure Layer  
# ✅ Can import: domain, application layers, external libraries
# ❌ Cannot import: presentation layer

# Presentation Layer (API/UI)
# ✅ Can import: domain, application layers, web frameworks
# ❌ Should minimize infrastructure imports
```

### Testing Strategy

- Write tests for interfaces first, before implementations
- Test domain logic independently of infrastructure
- Mock repository interfaces in UseCase tests
- Integration tests validate layer boundaries

```python
# ✅ Good - Test interface behavior
class TestCreateThoughtUseCase:
    async def test_creates_thought_successfully(self):
        # Arrange
        mock_repo = Mock(spec=ThoughtRepository)
        usecase = CreateThoughtUseCase(mock_repo)
        
        # Act & Assert - test business logic
```

This architecture ensures:
- **Testability**: Each layer can be tested in isolation
- **Flexibility**: Easy to swap implementations (PostgreSQL ↔ Redis)
- **Maintainability**: Clear separation of concerns
- **Scalability**: Layers can evolve independently