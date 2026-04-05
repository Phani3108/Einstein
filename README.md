# Personal Semantic Engine (Einstein)

[![Version](https://img.shields.io/badge/version-0.2.0-blue.svg)](https://github.com/codevalley/einstein/releases/tag/v0.2.0)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A unified personal data repository that transforms scattered thoughts, notes, and information into a searchable, intelligent knowledge base using semantic understanding and AI-powered insights.

## 🚀 Features

### ✅ Core Infrastructure (v0.2.0)
- **Thought Capture**: Store and organize personal thoughts, notes, and ideas
- **Semantic Understanding**: AI-powered entity extraction using LLM models
- **Vector Storage**: Semantic search using OpenAI embeddings and Pinecone
- **Knowledge Mapping**: Extract and store semantic relationships
- **Clean Architecture**: Domain-driven design with SOLID principles

### 🔄 In Development (v0.3.0)
- **REST API**: Complete API endpoints for all functionality
- **Advanced Search**: Natural language query processing
- **Knowledge Graphs**: Visualize connections between ideas and concepts
- **Real-time Processing**: Live semantic analysis and indexing

### 🎯 Planned Features
- **Privacy-First**: Your data stays under your control
- **Multi-modal Support**: Text, images, and documents
- **Export/Import**: Data portability and backup
- **Analytics**: Insights into your thinking patterns

## 🏗️ Architecture

Built with clean architecture principles ensuring maintainability and testability:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Presentation  │    │   Application   │    │     Domain      │
│                 │    │                 │    │                 │
│ • FastAPI       │───▶│ • Use Cases     │───▶│ • Entities      │
│ • REST APIs     │    │ • Workflows     │    │ • Repositories  │
│ • CLI Tools     │    │ • Orchestration │    │ • Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────────────────────────────────────────┘
│
▼
┌─────────────────┐
│ Infrastructure  │
│                 │
│ • PostgreSQL    │
│ • OpenAI API    │
│ • Pinecone      │
│ • LiteLLM       │
└─────────────────┘
```

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic
- **Database**: PostgreSQL with async support
- **AI/ML**: OpenAI GPT models, LiteLLM, vector embeddings
- **Vector DB**: Pinecone for semantic search
- **Testing**: pytest, pytest-asyncio, comprehensive coverage
- **Code Quality**: Black, isort, mypy, pre-commit hooks
- **Dependency Management**: Poetry
- **Architecture**: Clean Architecture, Domain-Driven Design

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Poetry (for dependency management)
- OpenAI API key
- Pinecone account (for vector storage)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/codevalley/einstein.git
cd einstein
```

2. **Install dependencies:**
```bash
poetry install
```

3. **Set up environment variables:**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/einstein
TEST_DATABASE_URL=postgresql+asyncpg://postgres:password@localhost/einstein_test

# OpenAI
OPENAI_API_KEY=your-openai-api-key-here

# Pinecone
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_ENVIRONMENT=your-pinecone-environment-here

# LLM Configuration
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.0
```

4. **Initialize the database:**
```bash
poetry run python scripts/init_db.py
```

5. **Run migrations:**
```bash
poetry run alembic upgrade head
```

6. **Verify installation:**
```bash
poetry run python verify_vector_implementation.py
```

## 🧪 Development

### Running Tests

```bash
# Run vector storage tests
poetry run python tests/infrastructure/services/run_tests.py

# Run architecture compliance check
poetry run python check_architecture.py

# Run all verification
poetry run python verify_vector_implementation.py
```

### Code Quality

```bash
# Pre-commit quality checks
poetry run python scripts/pre_commit_check.py

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy src/ --ignore-missing-imports
```

### Version Management

```bash
# Check current version
poetry run python scripts/version_manager.py --current

# Bump version
poetry run python scripts/version_manager.py --bump minor

# Create release tag
poetry run python scripts/version_manager.py --tag --message "Release v0.3.0"
```

## 📊 Current Status

### ✅ Completed (v0.2.0)
- [x] Core domain entities and repositories
- [x] LLM integration for entity extraction
- [x] Vector storage infrastructure (OpenAI + Pinecone)
- [x] Semantic search capabilities
- [x] Comprehensive test suite
- [x] Clean architecture compliance
- [x] Version control standards

### 🔄 In Progress (v0.3.0)
- [ ] REST API implementation
- [ ] API documentation with OpenAPI
- [ ] Rate limiting and security
- [ ] Client SDK development

### 🎯 Roadmap
- **v0.4.0**: Advanced Features (clustering, insights, export)
- **v1.0.0**: Production Release (monitoring, deployment, docs)

## 🤝 Contributing

We follow strict version control standards and code quality practices:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feat/amazing-feature`
3. **Follow our standards**: Check `.kiro/steering/version-control-standards.md`
4. **Run quality checks**: `poetry run python scripts/pre_commit_check.py`
5. **Commit with conventional format**: `feat: add amazing feature`
6. **Submit a pull request**

### Commit Standards

We use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features
- `fix:` Bug fixes  
- `docs:` Documentation changes
- `style:` Code formatting
- `refactor:` Code restructuring
- `test:` Adding tests
- `chore:` Maintenance tasks

## 📈 Performance & Quality

- **Test Coverage**: 100% for vector services
- **Architecture**: Clean Architecture compliance verified
- **Code Quality**: Black + isort + mypy
- **Type Safety**: Complete type annotations
- **Documentation**: Comprehensive docstrings and guides

## 🔒 Security & Privacy

- **API Keys**: Secure environment variable management
- **Data Isolation**: User-scoped vector operations
- **Input Validation**: Pydantic models with validation
- **Error Handling**: Domain-specific exceptions

## 📚 Documentation

- [Version Control Standards](.kiro/steering/version-control-standards.md)
- [Vector Implementation Summary](VECTOR_IMPLEMENTATION_SUMMARY.md)
- [LLM Configuration Guide](docs/llm_configuration_guide.md)
- [Changelog](CHANGELOG.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with clean architecture principles
- Inspired by domain-driven design
- Powered by OpenAI and Pinecone technologies