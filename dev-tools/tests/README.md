# Development Tests

Integration tests and standalone test runners for Faraday components.

## Test Categories

### Integration Tests
- `test_basic_integration.py` - Basic system integration tests
- `test_container_integration.py` - Dependency injection container tests
- `test_full_integration.py` - Complete end-to-end integration tests
- `test_timeline_integration.py` - Timeline feature integration tests
- `test_vector_services_only.py` - Vector service isolation tests

### Component Tests
- `test_llm_standalone.py` - LLM service standalone tests
- `test_ranking_functionality.py` - Search ranking algorithm tests
- `test_search_ranking.py` - Search result ranking tests

### Test Runners
- `run_llm_tests.py` - LLM service test runner
- `run_search_service_tests.py` - Search service test runner
- `run_vector_tests.py` - Vector service test runner

## Running Tests

```bash
# Run all integration tests
python dev-tools/tests/test_full_integration.py

# Run specific component tests
python dev-tools/tests/test_vector_services_only.py

# Run with test runners
python dev-tools/tests/run_vector_tests.py
```

## Purpose

These tests validate:
- Cross-component integration
- Service isolation and independence
- End-to-end workflows
- Performance and reliability

For unit tests, see the main `tests/` directory in the project root.