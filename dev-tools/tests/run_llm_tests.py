#!/usr/bin/env python
"""Run LLM tests directly without loading the application context."""

import os
import sys

import pytest

if __name__ == "__main__":
    # Add the current directory to the Python path
    sys.path.insert(0, os.path.abspath("."))

    # Run the LLM tests
    pytest.main(
        [
            "-v",
            "tests/infrastructure/llm/test_llm_service.py",
            "tests/infrastructure/llm/test_entity_extraction_service.py",
        ]
    )
