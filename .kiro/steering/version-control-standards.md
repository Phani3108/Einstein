---
inclusion: always
---

# Version Control Standards

This document defines version control standards and practices for the Personal Semantic Engine project to ensure consistent, traceable, and high-quality development.

## Commit Standards

### When to Commit

#### ✅ Commit Triggers
- **Task Completion**: After completing a task from the spec with all tests passing
- **Architecture Verification**: After confirming clean architecture compliance
- **Feature Milestones**: When a complete feature is implemented and tested
- **Bug Fixes**: After fixing bugs with appropriate tests
- **Documentation Updates**: After significant documentation changes

#### ❌ Do Not Commit
- Broken or failing tests
- Incomplete implementations
- Code that violates architecture principles
- Temporary debugging code
- Uncommitted merge conflicts

### Pre-Commit Checklist

Before every commit, ensure:

```bash
# 1. Run tests and verify they pass
poetry run python verify_implementation.py  # or relevant test script

# 2. Check architecture compliance
poetry run python check_architecture.py

# 3. Format code
poetry run black .
poetry run isort .

# 4. Type checking (if applicable)
poetry run mypy src/

# 5. Review changes
git diff --staged
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Commit Types
- **feat**: New feature implementation
- **fix**: Bug fixes
- **docs**: Documentation changes
- **style**: Code formatting (no logic changes)
- **refactor**: Code restructuring (no feature changes)
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build, etc.)
- **perf**: Performance improvements
- **ci**: CI/CD configuration changes

#### Examples
```bash
# Feature implementation
git commit -m "feat: implement vector storage infrastructure for semantic search

- Add OpenAI embedding service implementation
- Add Pinecone vector store service implementation  
- Implement vector indexing for thoughts and semantic entries
- Add vector similarity search with metadata filtering
- Create comprehensive unit and integration tests

Satisfies requirements 2.1, 2.2, and 2.4 for semantic search capabilities."

# Bug fix
git commit -m "fix(auth): resolve JWT token expiration handling

- Fix token refresh logic in authentication middleware
- Add proper error handling for expired tokens
- Update tests to cover edge cases

Fixes issue #123"

# Documentation
git commit -m "docs: add API documentation for vector search endpoints

- Document embedding generation endpoints
- Add vector search API examples
- Include authentication requirements"
```

## Versioning Strategy

### Semantic Versioning (SemVer)

Follow [Semantic Versioning](https://semver.org/) format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes to API or architecture
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Version Tagging

```bash
# Create and push version tags
git tag -a v0.1.0 -m "Initial release with core functionality"
git push origin v0.1.0
```

### Version Milestones

#### v0.1.0 - Foundation
- [ ] Core domain entities and repositories
- [ ] Basic CRUD operations
- [ ] Authentication system
- [ ] Database migrations

#### v0.2.0 - Intelligence Layer
- [ ] LLM integration for entity extraction
- [ ] Vector storage infrastructure
- [ ] Semantic search capabilities
- [ ] Entity relationship mapping

#### v0.3.0 - API Layer
- [ ] REST API implementation
- [ ] API documentation
- [ ] Rate limiting and security
- [ ] Client SDK

#### v1.0.0 - Production Ready
- [ ] Performance optimization
- [ ] Comprehensive monitoring
- [ ] Production deployment
- [ ] User documentation

## Changelog Management

### CHANGELOG.md Format

Maintain a `CHANGELOG.md` file following [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New features in development

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed

### Removed
- Features that have been removed

### Fixed
- Bug fixes

### Security
- Security improvements

## [0.2.0] - 2024-01-15

### Added
- Vector storage infrastructure for semantic search
- OpenAI embedding service integration
- Pinecone vector database support
- Semantic similarity search with metadata filtering
- Comprehensive test suite for vector operations

### Changed
- Updated dependency injection container for vector services
- Enhanced environment configuration for external APIs

### Fixed
- Resolved architecture compliance issues in service layer

## [0.1.0] - 2024-01-01

### Added
- Initial project structure with clean architecture
- Core domain entities (User, Thought, SemanticEntry)
- PostgreSQL repository implementations
- Basic authentication system
- Database migration framework
```

### Changelog Update Process

1. **During Development**: Add entries to `[Unreleased]` section
2. **Before Release**: Move unreleased items to new version section
3. **After Commit**: Update changelog with commit details

## Branch Strategy

### Main Branch Protection
- **main**: Production-ready code only
- All commits must pass CI/CD pipeline
- Require pull request reviews (when working in teams)

### Feature Development
```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feat/vector-storage-infrastructure

# Work on feature...
# Commit changes following standards

# Before merging back to main
git checkout main
git pull origin main
git checkout feat/vector-storage-infrastructure
git rebase main  # or merge main into feature branch

# Ensure all tests pass
poetry run python verify_implementation.py

# Merge to main (or create PR)
git checkout main
git merge feat/vector-storage-infrastructure
git push origin main
```

## Quality Gates

### Automated Checks

Create pre-commit hooks or CI/CD pipeline with:

```yaml
# .github/workflows/quality-check.yml
name: Quality Check
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Format check
        run: |
          poetry run black --check .
          poetry run isort --check-only .
      
      - name: Type check
        run: poetry run mypy src/
      
      - name: Run tests
        run: poetry run pytest
      
      - name: Architecture compliance
        run: poetry run python check_architecture.py
```

### Manual Review Checklist

Before each commit:

- [ ] All tests pass
- [ ] Architecture compliance verified
- [ ] Code formatted and linted
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped (if applicable)
- [ ] Commit message follows standards

## Release Process

### 1. Pre-Release Preparation
```bash
# Update version in pyproject.toml
# Update CHANGELOG.md
# Run full test suite
poetry run pytest
poetry run python verify_implementation.py
poetry run python check_architecture.py
```

### 2. Create Release
```bash
# Commit version changes
git add .
git commit -m "chore: bump version to v0.2.0"

# Create and push tag
git tag -a v0.2.0 -m "Release v0.2.0: Vector Storage Infrastructure"
git push origin main
git push origin v0.2.0
```

### 3. Post-Release
- Update documentation
- Notify stakeholders
- Plan next version features

## Tools and Automation

### Recommended Tools
- **pre-commit**: Automated code quality checks
- **commitizen**: Interactive commit message creation
- **semantic-release**: Automated versioning and changelog
- **GitHub Actions**: CI/CD pipeline

### Setup Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
# Install hooks
pre-commit install
```

## Documentation Standards

### Code Documentation
- Update docstrings for new/changed functions
- Update README.md for significant changes
- Maintain API documentation
- Update architecture diagrams

### Commit Documentation
- Reference issue numbers when applicable
- Explain the "why" not just the "what"
- Include breaking change notes
- Link to relevant documentation

## Rollback Strategy

### Quick Rollback
```bash
# Revert last commit
git revert HEAD

# Revert specific commit
git revert <commit-hash>

# Reset to previous version (use carefully)
git reset --hard <previous-commit>
```

### Version Rollback
```bash
# Checkout previous version
git checkout v0.1.0

# Create hotfix branch if needed
git checkout -b hotfix/critical-fix
```

This version control strategy ensures:
- **Traceability**: Every change is documented and traceable
- **Quality**: Automated checks prevent broken code from being committed
- **Consistency**: Standardized commit messages and versioning
- **Reliability**: Clear rollback procedures for issues
- **Collaboration**: Clear processes for team development

Follow these standards consistently to maintain a high-quality, maintainable codebase.