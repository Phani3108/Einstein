#!/usr/bin/env python3
"""Simple test runner for vector storage services."""

import asyncio
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Import test modules
from test_embedding_service import *
from test_vector_storage_integration import *
from test_vector_store_service import *

if __name__ == "__main__":
    # Run the tests using pytest programmatically
    import pytest

    # Run tests without conftest.py interference
    exit_code = pytest.main(
        [
            __file__.replace("test_runner.py", "test_embedding_service.py"),
            __file__.replace("test_runner.py", "test_vector_store_service.py"),
            __file__.replace("test_runner.py", "test_vector_storage_integration.py"),
            "-v",
            "--tb=short",
            "--no-cov",
        ]
    )

    sys.exit(exit_code)
