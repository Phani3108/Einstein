#!/usr/bin/env python3
"""Run vector storage tests."""

import os
import subprocess
import sys


def run_test_file(test_file):
    """Run a single test file."""
    print(f"\n{'='*60}")
    print(f"Running {test_file}")
    print("=" * 60)

    # Create a temporary test file that doesn't use conftest.py
    temp_test_content = f"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Import the test file content
exec(open('{test_file}').read())

# Run tests manually
if __name__ == "__main__":
    import unittest
    unittest.main(verbosity=2)
"""

    temp_file = f"temp_{os.path.basename(test_file)}"
    with open(temp_file, "w") as f:
        f.write(temp_test_content)

    try:
        result = subprocess.run(
            [sys.executable, temp_file], capture_output=True, text=True
        )
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def main():
    """Run all vector storage tests."""
    test_files = [
        "tests/infrastructure/services/test_embedding_service.py",
        "tests/infrastructure/services/test_vector_store_service.py",
        "tests/infrastructure/services/test_vector_storage_integration.py",
    ]

    all_passed = True
    for test_file in test_files:
        if os.path.exists(test_file):
            passed = run_test_file(test_file)
            all_passed = all_passed and passed
        else:
            print(f"Test file {test_file} not found")
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
