#!/usr/bin/env python
"""Validate clean architecture principles in codebase."""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set


class ArchitectureValidator:
    """Validates clean architecture rules."""

    LAYER_RULES = {
        "domain": {
            "allowed_imports": {
                "typing",
                "datetime",
                "enum",
                "pydantic",
                "abc",
                "uuid",
            },
            "forbidden_imports": {"sqlalchemy", "fastapi", "requests", "asyncpg"},
        },
        "application": {
            "allowed_layers": {"domain"},
            "forbidden_layers": {"infrastructure", "api", "cli"},
        },
        "infrastructure": {
            "allowed_layers": {"domain", "application"},
            "forbidden_layers": {"api", "cli"},
        },
        "api": {"allowed_layers": {"domain", "application"}, "forbidden_layers": set()},
        "cli": {
            "allowed_layers": {"domain", "application"},
            "forbidden_layers": {"api"},
        },
    }

    def validate_file(self, file_path: Path) -> List[str]:
        """Validate a single Python file against architecture rules."""
        violations = []

        # Determine layer from file path
        layer = self._get_layer(file_path)
        if not layer:
            return violations

        # Parse file and check imports
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())

            violations.extend(self._check_imports(tree, file_path, layer))
            violations.extend(self._check_layer_dependencies(tree, file_path, layer))

        except Exception as e:
            violations.append(f"{file_path}: Failed to parse - {e}")

        return violations

    def _get_layer(self, file_path: Path) -> str:
        """Determine which architecture layer a file belongs to."""
        parts = file_path.parts
        if "domain" in parts:
            return "domain"
        elif "application" in parts:
            return "application"
        elif "infrastructure" in parts:
            return "infrastructure"
        elif "api" in parts:
            return "api"
        elif "cli" in parts:
            return "cli"
        return ""

    def _check_imports(self, tree: ast.AST, file_path: Path, layer: str) -> List[str]:
        """Check if imports violate layer rules."""
        violations = []
        rules = self.LAYER_RULES.get(layer, {})
        forbidden = rules.get("forbidden_imports", set())

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = self._get_module_name(node)
                if any(forbidden_mod in module_name for forbidden_mod in forbidden):
                    violations.append(
                        f"{file_path}:{node.lineno}: "
                        f"Layer '{layer}' cannot import '{module_name}'"
                    )

        return violations

    def _check_layer_dependencies(
        self, tree: ast.AST, file_path: Path, layer: str
    ) -> List[str]:
        """Check if layer dependencies are correct."""
        violations = []
        rules = self.LAYER_RULES.get(layer, {})
        forbidden_layers = rules.get("forbidden_layers", set())

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden_layer in forbidden_layers:
                    if forbidden_layer in node.module.split("."):
                        violations.append(
                            f"{file_path}:{node.lineno}: "
                            f"Layer '{layer}' cannot depend on layer '{forbidden_layer}'"
                        )

        return violations

    def _get_module_name(self, node) -> str:
        """Extract module name from import node."""
        if isinstance(node, ast.Import):
            return node.names[0].name
        elif isinstance(node, ast.ImportFrom):
            return node.module or ""
        return ""


def main():
    """Run architecture validation on all Python files."""
    validator = ArchitectureValidator()
    violations = []

    # Check all Python files in src directory
    src_path = Path("src")
    if not src_path.exists():
        print("No src directory found")
        return 0

    for py_file in src_path.rglob("*.py"):
        violations.extend(validator.validate_file(py_file))

    if violations:
        print("Architecture violations found:")
        for violation in violations:
            print(f"  {violation}")
        return 1

    print("Architecture validation passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
