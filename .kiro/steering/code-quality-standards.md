---
inclusion: always
---

# Code Quality Standards

This document defines code quality standards and tooling requirements for the Personal Semantic Engine project.

## Code Formatting and Style

### Black Code Formatter
- All Python code must be formatted with Black
- Line length: 88 characters (Black default)
- No exceptions to Black formatting rules

```bash
# Format all code
black .

# Check formatting
black --check .
```

### Import Sorting with isort
- Imports organized with isort, compatible with Black
- Group imports: standard library, third-party, local

```bash
# Sort imports
isort .

# Check import sorting
isort --check-only .
```

## Type Safety with Pydantic

### Domain Models
- All domain entities must inherit from Pydantic BaseModel
- Use Pydantic validators for business rule validation
- Leverage Pydantic's automatic serialization/deserialization

```python
# ✅ Good - Pydantic domain model
from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional

class Thought(BaseModel):
    id: str
    content: str
    user_id: str
    timestamp: datetime
    metadata: Optional[dict] = None
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Content cannot be empty')
        return v
    
    class Config:
        # Ensure immutability for domain objects
        allow_mutation = False
```

### API Models
- Separate Pydantic models for API requests/responses
- Use Pydantic's automatic OpenAPI schema generation
- Validate all input at API boundaries

```python
# ✅ Good - API models separate from domain
class CreateThoughtRequest(BaseModel):
    content: str
    metadata: Optional[dict] = None

class ThoughtResponse(BaseModel):
    id: str
    content: str
    timestamp: datetime
    
    @classmethod
    def from_domain(cls, thought: Thought) -> 'ThoughtResponse':
        return cls(
            id=thought.id,
            content=thought.content,
            timestamp=thought.timestamp
        )
```

## Type Hints and mypy

### Type Annotations
- All functions must have complete type annotations
- Use `typing` module for complex types
- No `Any` types unless absolutely necessary

```python
# ✅ Good - Complete type annotations
from typing import List, Optional, Protocol

class ThoughtRepository(Protocol):
    async def save(self, thought: Thought) -> Thought: ...
    async def find_by_user(self, user_id: str) -> List[Thought]: ...
    async def find_by_id(self, thought_id: str) -> Optional[Thought]: ...
```

### mypy Configuration
```ini
# mypy.ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
```

## Code Structure Standards

### File Organization
```
src/
├── domain/
│   ├── entities/          # Pydantic domain models
│   ├── repositories/      # Repository interfaces (ABC)
│   └── services/          # Service interfaces (ABC)
├── application/
│   ├── usecases/         # Business logic orchestration
│   └── services/         # Application services
├── infrastructure/
│   ├── database/         # Database implementations
│   ├── external/         # External API clients
│   └── repositories/     # Repository implementations
└── presentation/
    ├── api/              # FastAPI routes and models
    └── cli/              # CLI interface
```

### Naming Conventions
- **Classes**: PascalCase (`ThoughtRepository`)
- **Functions/Methods**: snake_case (`create_thought`)
- **Variables**: snake_case (`user_id`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_CONTENT_LENGTH`)
- **Files**: snake_case (`thought_repository.py`)

## Documentation Standards

### Docstrings
- Use Google-style docstrings for all public functions/classes
- Include type information in docstrings for complex types

```python
def extract_entities(content: str, metadata: Optional[dict] = None) -> List[SemanticEntry]:
    """Extract semantic entities from thought content.
    
    Args:
        content: The raw thought content to analyze
        metadata: Optional metadata context for extraction
        
    Returns:
        List of extracted semantic entries with confidence scores
        
    Raises:
        EntityExtractionError: If extraction fails or content is invalid
    """
```

### Code Comments
- Explain **why**, not **what**
- Focus on business logic and architectural decisions
- Avoid obvious comments

```python
# ✅ Good - Explains business reasoning
# We extract entities asynchronously to avoid blocking the main thread
# during LLM API calls, which can take 2-5 seconds
entities = await self._entity_extractor.extract_entities(thought.content)

# ❌ Bad - States the obvious
# Call the extract entities method
entities = await self._entity_extractor.extract_entities(thought.content)
```

## Error Handling Standards

### Custom Exceptions
- Create domain-specific exceptions
- Inherit from appropriate base exceptions
- Include helpful error messages

```python
# Domain exceptions
class DomainError(Exception):
    """Base exception for domain layer errors."""
    pass

class ThoughtNotFoundError(DomainError):
    """Raised when a thought cannot be found."""
    
    def __init__(self, thought_id: str):
        super().__init__(f"Thought with ID {thought_id} not found")
        self.thought_id = thought_id
```

### Error Propagation
- Let domain exceptions bubble up through layers
- Convert to appropriate HTTP status codes at API layer
- Log errors with structured information

## Testing Standards

### Test Structure
- Follow AAA pattern: Arrange, Act, Assert
- One assertion per test when possible
- Descriptive test names that explain the scenario

```python
class TestCreateThoughtUseCase:
    async def test_creates_thought_with_valid_input_successfully(self):
        # Arrange
        mock_repo = Mock(spec=ThoughtRepository)
        mock_extractor = Mock(spec=EntityExtractionService)
        usecase = CreateThoughtUseCase(mock_repo, mock_extractor)
        
        thought = Thought(
            id="test-id",
            content="Test thought",
            user_id="user-123",
            timestamp=datetime.now()
        )
        
        # Act
        result = await usecase.execute(thought)
        
        # Assert
        assert result.id == "test-id"
        mock_repo.save.assert_called_once_with(thought)
```

### Test Coverage
- Minimum 90% code coverage for domain and application layers
- 80% coverage for infrastructure layer
- Focus on testing business logic, not framework code

### Test Categories
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test layer boundaries and external dependencies
- **Contract Tests**: Validate interface implementations
- **End-to-End Tests**: Test complete user scenarios

## Performance Standards

### Async/Await Usage
- Use async/await for all I/O operations
- Avoid blocking calls in async functions
- Use asyncio.gather() for concurrent operations

```python
# ✅ Good - Concurrent processing
async def process_thought(self, thought: Thought) -> ProcessedThought:
    entities_task = self._extract_entities(thought.content)
    embeddings_task = self._generate_embeddings(thought.content)
    
    entities, embeddings = await asyncio.gather(entities_task, embeddings_task)
    return ProcessedThought(thought, entities, embeddings)
```

### Database Queries
- Use connection pooling
- Implement proper indexing
- Avoid N+1 query problems
- Use database transactions appropriately

## Security Standards

### Input Validation
- Validate all inputs at API boundaries using Pydantic
- Sanitize user content before processing
- Implement rate limiting

### Authentication/Authorization
- Use JWT tokens with proper expiration
- Implement role-based access control
- Hash passwords with bcrypt

### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS for all communications
- Implement proper CORS policies

This ensures our codebase maintains high quality, consistency, and architectural integrity throughout development.