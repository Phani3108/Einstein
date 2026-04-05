# Development Tools

This directory contains development and testing utilities for the Faraday Personal Semantic Engine project.

## Directory Structure

### `tests/`
Integration tests and standalone test scripts for various components:
- `test_*.py` - Integration test scripts
- `run_*.py` - Standalone test runners

### `verification/`
Verification scripts to validate implementation completeness:
- `verify_*.py` - Implementation verification scripts
- `check_architecture.py` - Architecture compliance checker

### `summaries/`
Implementation summaries and documentation from development:
- `*_IMPLEMENTATION_SUMMARY.md` - Detailed implementation summaries
- Task completion documentation

## Purpose

These tools are used for:
- **Development Testing**: Validate components during development
- **Implementation Verification**: Ensure requirements are met
- **Architecture Compliance**: Maintain clean architecture principles
- **Documentation**: Track implementation progress and decisions

## Usage

### Running Tests
```bash
# Run integration tests
python dev-tools/tests/test_basic_integration.py

# Run specific component tests
python dev-tools/tests/run_vector_tests.py
```

### Verification
```bash
# Verify implementation completeness
python dev-tools/verification/verify_search_implementation.py

# Check architecture compliance
python dev-tools/verification/check_architecture.py
```

### Documentation
Implementation summaries provide detailed documentation of how each component was built and verified.

## For Production Users

If you're using Faraday in production, you probably don't need these development tools. See the main project documentation in the root directory and `docs/` folder instead.