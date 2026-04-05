# Integration Tests

This directory contains integration tests for the Einstein CLI that test complete workflows and feature interactions.

## Test Files

### Core Functionality Tests
- `test_cli_integration.py` - End-to-end CLI command testing
- `test_thought_commands_demo.py` - Thought management command integration
- `test_search_integration.py` - Search functionality integration tests
- `test_search_demo.py` - Search feature demonstrations

### Interactive Mode Tests
- `test_interactive_mode.py` - Interactive mode functionality
- `test_interactive_integration.py` - Interactive mode integration tests
- `test_smart_interactive.py` - Advanced interactive features

### Caching and Sync Tests
- `test_cache_integration.py` - Cache system integration tests
- `test_cli_with_cache.py` - CLI with caching functionality
- `test_sync_command.py` - Sync command integration tests

### Help System Tests
- `test_help_system.py` - Comprehensive help system testing

## Running Tests

```bash
# Run all integration tests
python -m pytest tests/integration/

# Run specific test file
python -m pytest tests/integration/test_cli_integration.py

# Run with verbose output
python -m pytest tests/integration/ -v
```

## Purpose

These integration tests verify:
- Complete user workflows work end-to-end
- Different components integrate properly
- Real-world usage scenarios function correctly
- Performance and reliability under various conditions

For unit tests, see the `tests/` directory. For development verification, see `docs/development/`.