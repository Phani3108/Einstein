---
inclusion: manual
contextKey: hooks
---

# Development Hooks and Automation

This document defines automated hooks and checks to enforce code quality and architectural principles during development.

## Pre-commit Hooks

### Code Quality Checks
Set up pre-commit hooks to run automatically before each commit:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-requests]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: local
    hooks:
      - id: architecture-check
        name: Clean Architecture Validation
        entry: python scripts/validate_architecture.py
        language: system
        files: \.py$
```

### Architecture Validation Hook
Create a custom hook to validate clean architecture principles:

```python
# scripts/validate_architecture.py
"""Validate clean architecture principles in codebase."""

import ast
import sys
from pathlib import Path
from typing import List, Set

class ArchitectureValidator:
    """Validates clean architecture rules."""
    
    LAYER_RULES = {
        'domain': {
            'allowed_imports': {'typing', 'datetime', 'enum', 'pydantic', 'abc'},
            'forbidden_imports': {'sqlalchemy', 'fastapi', 'requests', 'asyncpg'}
        },
        'application': {
            'allowed_layers': {'domain'},
            'forbidden_layers': {'infrastructure', 'presentation'}
        },
        'infrastructure': {
            'allowed_layers': {'domain', 'application'},
            'forbidden_layers': {'presentation'}
        },
        'presentation': {
            'allowed_layers': {'domain', 'application'},
            'forbidden_layers': {'infrastructure'}
        }
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
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
                
            violations.extend(self._check_imports(tree, file_path, layer))
            violations.extend(self._check_layer_dependencies(tree, file_path, layer))
            
        except Exception as e:
            violations.append(f"{file_path}: Failed to parse - {e}")
            
        return violations
    
    def _get_layer(self, file_path: Path) -> str:
        """Determine which architecture layer a file belongs to."""
        parts = file_path.parts
        if 'domain' in parts:
            return 'domain'
        elif 'application' in parts:
            return 'application'
        elif 'infrastructure' in parts:
            return 'infrastructure'
        elif 'presentation' in parts or 'api' in parts:
            return 'presentation'
        return ''
    
    def _check_imports(self, tree: ast.AST, file_path: Path, layer: str) -> List[str]:
        """Check if imports violate layer rules."""
        violations = []
        rules = self.LAYER_RULES.get(layer, {})
        forbidden = rules.get('forbidden_imports', set())
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = self._get_module_name(node)
                if any(forbidden_mod in module_name for forbidden_mod in forbidden):
                    violations.append(
                        f"{file_path}:{node.lineno}: "
                        f"Layer '{layer}' cannot import '{module_name}'"
                    )
                    
        return violations
    
    def _check_layer_dependencies(self, tree: ast.AST, file_path: Path, layer: str) -> List[str]:
        """Check if layer dependencies are correct."""
        violations = []
        rules = self.LAYER_RULES.get(layer, {})
        forbidden_layers = rules.get('forbidden_layers', set())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for forbidden_layer in forbidden_layers:
                    if forbidden_layer in node.module:
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
            return node.module or ''
        return ''

def main():
    """Run architecture validation on all Python files."""
    validator = ArchitectureValidator()
    violations = []
    
    # Check all Python files in src directory
    src_path = Path('src')
    if not src_path.exists():
        print("No src directory found")
        return 0
        
    for py_file in src_path.rglob('*.py'):
        violations.extend(validator.validate_file(py_file))
    
    if violations:
        print("Architecture violations found:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    
    print("Architecture validation passed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

## IDE Integration Hooks

### VS Code Settings
```json
{
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

## Continuous Integration Hooks

### GitHub Actions Workflow
```yaml
# .github/workflows/quality-check.yml
name: Code Quality Check

on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
        
    - name: Run Black
      run: poetry run black --check .
      
    - name: Run isort
      run: poetry run isort --check-only .
      
    - name: Run mypy
      run: poetry run mypy src/
      
    - name: Run flake8
      run: poetry run flake8 src/
      
    - name: Validate Architecture
      run: poetry run python scripts/validate_architecture.py
      
    - name: Run Tests
      run: poetry run pytest --cov=src --cov-report=xml
      
    - name: Upload Coverage
      uses: codecov/codecov-action@v3
```

## Development Workflow Hooks

### Test-First Development Hook
```python
# scripts/test_first_check.py
"""Ensure tests exist before implementation."""

import sys
from pathlib import Path

def check_test_coverage():
    """Check that all implementation files have corresponding tests."""
    src_path = Path('src')
    tests_path = Path('tests')
    
    missing_tests = []
    
    for py_file in src_path.rglob('*.py'):
        if py_file.name == '__init__.py':
            continue
            
        # Calculate expected test file path
        relative_path = py_file.relative_to(src_path)
        test_file = tests_path / f"test_{relative_path}"
        
        if not test_file.exists():
            missing_tests.append(str(relative_path))
    
    if missing_tests:
        print("Missing test files:")
        for missing in missing_tests:
            print(f"  tests/test_{missing}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(check_test_coverage())
```

### Interface-First Development Hook
```python
# scripts/interface_check.py
"""Ensure interfaces are defined before implementations."""

import ast
import sys
from pathlib import Path

def check_interfaces():
    """Check that implementations have corresponding interfaces."""
    violations = []
    
    # Check repository implementations
    repo_impl_path = Path('src/infrastructure/repositories')
    if repo_impl_path.exists():
        for py_file in repo_impl_path.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
                
            violations.extend(check_repository_interface(py_file))
    
    if violations:
        print("Interface violations:")
        for violation in violations:
            print(f"  {violation}")
        return 1
    
    return 0

def check_repository_interface(impl_file: Path):
    """Check if repository implementation has corresponding interface."""
    violations = []
    
    with open(impl_file, 'r') as f:
        tree = ast.parse(f.read())
    
    # Find class definitions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            if 'Repository' in class_name and not any(
                isinstance(base, ast.Name) and 'Repository' in base.id 
                for base in node.bases
            ):
                violations.append(
                    f"{impl_file}: Class {class_name} should implement a repository interface"
                )
    
    return violations

if __name__ == '__main__':
    sys.exit(check_interfaces())
```

## Makefile for Common Tasks

```makefile
# Makefile
.PHONY: format lint test architecture-check install

install:
	poetry install
	pre-commit install

format:
	poetry run black .
	poetry run isort .

lint:
	poetry run flake8 src/
	poetry run mypy src/

test:
	poetry run pytest --cov=src --cov-report=term-missing

architecture-check:
	poetry run python scripts/validate_architecture.py

quality-check: format lint architecture-check test
	@echo "All quality checks passed!"

clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/
```

## Usage Instructions

1. **Setup Development Environment**:
   ```bash
   make install
   ```

2. **Run Quality Checks**:
   ```bash
   make quality-check
   ```

3. **Format Code**:
   ```bash
   make format
   ```

4. **Validate Architecture**:
   ```bash
   make architecture-check
   ```

These hooks ensure that:
- Code is consistently formatted
- Type safety is maintained
- Architecture principles are enforced
- Tests are written before implementations
- Interfaces are defined before concrete classes
- All quality standards are met before code is committed