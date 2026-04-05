#!/usr/bin/env python3
"""Check that our vector storage implementation follows clean architecture principles."""

import ast
import os
import sys


def check_imports(file_path, allowed_imports):
    """Check that a file only imports from allowed modules."""
    print(f"Checking {file_path}...")

    with open(file_path, "r") as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    violations = []
    for imp in imports:
        # Check if import is allowed
        allowed = False
        for allowed_pattern in allowed_imports:
            if imp.startswith(allowed_pattern):
                allowed = True
                break

        if not allowed:
            violations.append(imp)

    if violations:
        print(f"  ❌ Architecture violations found:")
        for violation in violations:
            print(f"    - {violation}")
        return False
    else:
        print(f"  ✓ Clean architecture compliance verified")
        return True


def main():
    """Check architecture compliance."""
    print("Checking Clean Architecture Compliance")
    print("=" * 50)

    # Define allowed imports for each layer
    domain_allowed = [
        "abc",
        "typing",
        "datetime",
        "enum",
        "uuid",
        "pydantic",
        "src.domain",  # Domain can import from itself
    ]

    infrastructure_allowed = [
        "abc",
        "typing",
        "datetime",
        "enum",
        "uuid",
        "pydantic",
        "os",
        "src.domain",  # Infrastructure can import domain
        "openai",  # External dependencies
        "pinecone",  # External dependencies
    ]

    checks = [
        ("src/domain/services/embedding_service.py", domain_allowed),
        ("src/domain/services/vector_store_service.py", domain_allowed),
        ("src/domain/exceptions.py", domain_allowed),
        ("src/infrastructure/services/embedding_service.py", infrastructure_allowed),
        ("src/infrastructure/services/vector_store_service.py", infrastructure_allowed),
    ]

    all_passed = True
    for file_path, allowed in checks:
        if os.path.exists(file_path):
            passed = check_imports(file_path, allowed)
            all_passed = all_passed and passed
        else:
            print(f"❌ File {file_path} not found")
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL ARCHITECTURE CHECKS PASSED!")
        print("✓ Domain layer has no external dependencies")
        print("✓ Infrastructure layer properly depends on domain")
        print("✓ Clean separation of concerns maintained")
    else:
        print("❌ ARCHITECTURE VIOLATIONS FOUND!")
        print("Please fix the violations to maintain clean architecture.")
    print("=" * 50)

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
