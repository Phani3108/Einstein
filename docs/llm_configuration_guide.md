# LLM Configuration Guide

This guide provides detailed information on configuring and customizing the LLM-based entity extraction service in the Personal Semantic Engine.

## Architecture Overview

The LLM integration follows clean architecture principles:

1. **Domain Layer**: Defines the `EntityExtractionService` interface
2. **Infrastructure Layer**: Implements the interface with `LLMEntityExtractionService`
3. **Configuration**: External configuration for models, prompts, and schemas

## LLM Service

The `LLMService` class provides a unified interface to multiple LLM providers through LiteLLM:

```python
from src.infrastructure.llm.llm_service import LLMService

# Create with default configuration (from env vars and config files)
llm_service = LLMService()

# Or with specific parameters
llm_service = LLMService(
    model="gpt-4",
    temperature=0.2,
    max_tokens=2048
)

# Generate text
response = await llm_service.generate(
    prompt="What is the capital of France?",
    system_prompt="You are a helpful assistant."
)

# Generate structured JSON
response = await llm_service.generate(
    prompt="Extract entities from: John visited Paris last week.",
    system_prompt="Extract named entities.",
    json_mode=True,
    json_schema={"type": "object", "properties": {"entities": {"type": "array"}}}
)
```

## Entity Extraction Service

The `LLMEntityExtractionService` extracts semantic entities from text:

```python
from src.infrastructure.llm.entity_extraction_service import LLMEntityExtractionService

# Create with default configuration
extraction_service = LLMEntityExtractionService(llm_service)

# Extract entities from text
entities = await extraction_service.extract_entities(
    content="John met Sarah in New York yesterday.",
    thought_id=uuid.uuid4()
)
```

## Customizing Prompts

All prompts are stored as external files in `src/infrastructure/llm/prompts/`:

### System Prompt (`entity_extraction_system.txt`)

This file contains instructions for the LLM. Example:

```
You are an expert entity extraction system for a personal semantic engine.
Your task is to analyze text and extract meaningful entities along with their relationships.
...
```

### User Prompt Template (`entity_extraction.txt`)

This file contains the template for user prompts with placeholders:

```
Please extract all relevant entities from the following text:

TEXT:
{CONTENT}

METADATA:
{METADATA}

Extract entities and their relationships, and format your response as JSON.
```

### JSON Schema (`entity_extraction_schema.json`)

This file defines the structure for LLM output:

```json
{
  "type": "object",
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "type": { 
            "type": "string",
            "enum": ["PERSON", "LOCATION", "DATE", "ACTIVITY", "EMOTION", "ORGANIZATION", "EVENT"]
          },
          "value": { "type": "string" },
          "confidence": { "type": "number" },
          "context": { "type": "string" },
          "relationships": { "type": "array" }
        }
      }
    }
  }
}
```

## LLM Provider Configuration

The `llm_config.json` file configures available LLM providers and models:

```json
{
  "providers": {
    "openai": {
      "models": {
        "gpt-4": {
          "description": "OpenAI GPT-4 model",
          "max_tokens": 8192,
          "default_temperature": 0.0
        },
        "gpt-3.5-turbo": {
          "description": "OpenAI GPT-3.5 Turbo model",
          "max_tokens": 4096,
          "default_temperature": 0.0
        }
      }
    },
    "anthropic": {
      "models": {
        "claude-3-opus": {
          "description": "Anthropic Claude 3 Opus model",
          "max_tokens": 4096,
          "default_temperature": 0.0
        }
      }
    }
  },
  "default_provider": "openai",
  "default_model": "gpt-4"
}
```

## Environment Variables

Configure your LLM settings in the `.env` file:

```
# LLM Configuration
LLM_MODEL=gpt-4                # Default model to use
LLM_TEMPERATURE=0.0            # Temperature for generation
LLM_MAX_TOKENS=4096            # Maximum tokens to generate

# API Keys for different providers
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
DEEPSEEK_API_KEY=your-deepseek-api-key-here
```

## Best Practices

1. **Prompt Engineering**:
   - Keep system prompts clear and specific
   - Use examples in prompts for better results
   - Test prompts with different models

2. **JSON Schema**:
   - Define strict schemas for structured output
   - Include enums for constrained values
   - Validate LLM output against schemas

3. **Error Handling**:
   - Always handle LLM API errors gracefully
   - Implement retry logic for transient failures
   - Validate and sanitize LLM responses

4. **Cost Optimization**:
   - Use smaller models for simpler tasks
   - Optimize prompt length to reduce token usage
   - Cache common responses when appropriate

5. **Testing**:
   - Mock LLM responses in unit tests
   - Create test fixtures for common scenarios
   - Test with multiple LLM providers