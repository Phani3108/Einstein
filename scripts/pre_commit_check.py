#!/usr/bin/env python3
"""Pre-commit quality checks for the Personal Semantic Engine."""

import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and return success status."""
    print(f"Running {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✓ {description} passed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stdout)
        print(e.stderr)
        return False


def main():
    """Run all pre-commit checks."""
    print("Running Pre-Commit Quality Checks")
    print("=" * 50)

    checks = [
        ("poetry run black --check .", "Code formatting check (Black)"),
        ("poetry run isort --check-only .", "Import sorting check (isort)"),
        ("poetry run mypy src/ --ignore-missing-imports", "Type checking (MyPy)"),
    ]

    # Add test checks if test files exist
    if Path("verify_vector_implementation.py").exists():
        checks.append(
            (
                "poetry run python verify_vector_implementation.py",
                "Vector implementation tests",
            )
        )

    if Path("check_architecture.py").exists():
        checks.append(
            ("poetry run python check_architecture.py", "Architecture compliance check")
        )

    # Run pytest if tests directory exists
    if Path("tests").exists():
        checks.append(("poetry run pytest tests/ -x", "Unit tests"))

    all_passed = True
    for command, description in checks:
        if not run_command(command, description):
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL PRE-COMMIT CHECKS PASSED!")
        print("Ready to commit.")
    else:
        print("❌ SOME CHECKS FAILED!")
        print("Please fix the issues before committing.")
    print("=" * 50)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
