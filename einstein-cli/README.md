# Einstein CLI

A powerful command-line interface for the Einstein Personal Semantic Engine that enables you to manage your thoughts, perform semantic searches, and analyze your personal knowledge base from the terminal.

## Features

- 🧠 **Thought Management**: Add, search, and organize your thoughts
- 🔍 **Semantic Search**: Find thoughts using natural language queries
- ⚙️ **Configuration Management**: Flexible configuration with platform-specific defaults
- 🔐 **Authentication**: Secure login and token management
- 📊 **Multiple Output Formats**: Human-readable and JSON output modes
- 🎨 **Rich Terminal UI**: Beautiful, colorized output with Rich library
- 🌐 **Cross-Platform**: Works on Windows, macOS, and Linux

## Installation

### From PyPI (when published)
```bash
pip install einstein-cli
```

### Development Installation
```bash
git clone <repository-url>
cd einstein-cli
poetry install
```

## Quick Start

1. **Configure your Einstein instance**:
   ```bash
   einstein config set api.url http://localhost:8001
   ```

2. **Login to your account**:
   ```bash
   einstein login
   ```

3. **Add your first thought**:
   ```bash
   einstein thoughts add "Had an amazing coffee meeting with Sarah today"
   ```

4. **Search your thoughts**:
   ```bash
   einstein thoughts search "coffee meetings"
   ```

## Commands Overview

### Configuration Commands

The `einstein config` command group manages CLI configuration:

```bash
# Show all configuration
einstein config show

# Get specific configuration value
einstein config get api.url

# Set configuration values
einstein config set api.url http://localhost:8001
einstein config set output.colors true
einstein config set api.timeout 60

# Reset to defaults
einstein config reset

# Show config file location
einstein config path
```

### Authentication Commands

```bash
# Login to your Einstein instance
einstein auth login

# Check login status
einstein auth status

# Logout
einstein auth logout
```

### Thought Management Commands

```bash
# Add a new thought
einstein thoughts add "Your thought content here"

# Search thoughts
einstein thoughts search "search query"

# List recent thoughts
einstein thoughts list

# Get specific thought by ID
einstein thoughts get <thought-id>
```

### Global Options

All commands support these global options:

```bash
# Use custom config file
einstein --config /path/to/config.toml <command>

# Override API URL
einstein --api-url http://custom-server:8001 <command>

# JSON output mode
einstein --json <command>

# Verbose output
einstein --verbose <command>
```

## Configuration

### Configuration File Locations

The CLI stores configuration in platform-specific locations:

- **Windows**: `%APPDATA%\einstein\config.toml`
- **macOS**: `~/Library/Application Support/einstein/config.toml`
- **Linux**: `~/.config/einstein/config.toml`

### Configuration Structure

```toml
[api]
url = "http://localhost:8001"
timeout = 30

[auth]
auto_login = true
remember_token = true

[output]
colors = true
pager = "auto"
max_results = 20

[cache]
enabled = true
max_size_mb = 100
sync_interval = 300
```

### Configuration Options

#### API Settings
- `api.url`: Einstein server URL (default: `http://localhost:8001`)
- `api.timeout`: Request timeout in seconds (default: `30`)

#### Authentication Settings
- `auth.auto_login`: Automatically attempt login when needed (default: `true`)
- `auth.remember_token`: Remember authentication tokens (default: `true`)

#### Output Settings
- `output.colors`: Enable colored output (default: `true`)
- `output.pager`: Pager for long output (`auto`, `less`, `more`, `none`) (default: `auto`)
- `output.max_results`: Maximum results to display (default: `20`)

#### Cache Settings
- `cache.enabled`: Enable local caching (default: `true`)
- `cache.max_size_mb`: Maximum cache size in MB (default: `100`)
- `cache.sync_interval`: Cache sync interval in seconds (default: `300`)

## Examples

### Basic Usage

```bash
# Configure your server
einstein config set api.url https://my-einstein-server.com

# Login
einstein auth login

# Add some thoughts
einstein thoughts add "Learning about semantic search today"
einstein thoughts add "Great book recommendation: 'Thinking, Fast and Slow'"
einstein thoughts add "Coffee shop idea: AI-powered menu recommendations"

# Search for thoughts
einstein thoughts search "book recommendations"
einstein thoughts search "AI ideas"

# List recent thoughts
einstein thoughts list --limit 10
```

### JSON Output Mode

```bash
# Get configuration as JSON
einstein --json config show

# Search with JSON output
einstein --json thoughts search "coffee" | jq '.results[].content'

# Get thought details as JSON
einstein --json thoughts get abc123 | jq '.timestamp'
```

### Advanced Configuration

```bash
# Set up for development environment
einstein config set api.url http://localhost:8001
einstein config set api.timeout 60
einstein config set output.max_results 50

# Disable colors for scripting
einstein config set output.colors false

# Configure caching
einstein config set cache.max_size_mb 200
einstein config set cache.sync_interval 600
```

## Error Handling

The CLI provides helpful error messages for common issues:

```bash
# Invalid configuration values
$ einstein config set api.timeout "not_a_number"
💥 Invalid configuration: Invalid configuration value for 'api.timeout': 
   Input should be a valid integer

# Missing configuration keys
$ einstein config get nonexistent.key
💥 Configuration key 'nonexistent.key' not found

# Connection issues
$ einstein thoughts list
💥 Connection Error: Could not connect to Einstein server at http://localhost:8001
   Please check your configuration and server status.
```

## Troubleshooting

### Common Issues

1. **Configuration file not found**:
   ```bash
   # Check config file location
   einstein config path
   
   # Reset to defaults if corrupted
   einstein config reset
   ```

2. **Connection refused**:
   ```bash
   # Check server URL
   einstein config get api.url
   
   # Update if needed
   einstein config set api.url http://correct-server:8001
   ```

3. **Authentication issues**:
   ```bash
   # Check login status
   einstein auth status
   
   # Re-login if needed
   einstein auth logout
   einstein auth login
   ```

### Debug Mode

Enable verbose output for debugging:

```bash
einstein --verbose thoughts search "debug query"
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd einstein-cli

# Install dependencies
poetry install

# Run CLI in development
poetry run einstein --help

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=einstein_cli

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy src/
```

### Project Structure

```
einstein-cli/
├── src/einstein_cli/           # Main CLI package
│   ├── commands/              # Command implementations
│   ├── main.py               # CLI entry point
│   ├── api.py                # API client
│   ├── auth.py               # Authentication
│   ├── config.py             # Configuration management
│   ├── cache.py              # Local caching
│   ├── cached_api.py         # Cached API client
│   ├── interactive.py        # Interactive mode
│   └── output.py             # Output formatting
├── tests/                    # Unit tests
│   └── integration/          # Integration tests
├── docs/                     # User documentation
│   └── development/          # Development documentation
├── examples/                 # Example scripts and demos
├── completions/              # Shell completion scripts
├── scripts/                  # Installation and utility scripts
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/test_config.py

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=einstein_cli --cov-report=html
```

### Code Quality

The project follows strict code quality standards:

```bash
# Format code
poetry run black .

# Sort imports
poetry run isort .

# Type checking
poetry run mypy src/

# All quality checks
poetry run black . && poetry run isort . && poetry run mypy src/ && poetry run pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- 📖 Documentation: [Link to docs]
- 🐛 Bug Reports: [Link to issues]
- 💬 Discussions: [Link to discussions]
- 📧 Email: team@einstein.dev