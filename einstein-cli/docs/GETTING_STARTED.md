# Getting Started with Einstein CLI

Welcome to Einstein CLI! This guide will help you get up and running in just a few minutes.

## Quick Start

### 1. Installation

```bash
# Install from PyPI (when available)
pip install einstein-cli

# Or install from source
git clone <repository-url>
cd einstein-cli
pip install -e .
```

### 2. First-Time Setup

Configure your Einstein server:

```bash
einstein config set api.url http://localhost:8001
```

Login to your account:

```bash
einstein auth login
```

Verify everything is working:

```bash
einstein auth status
```

### 3. Your First Thought

Add your first thought:

```bash
einstein thoughts add "This is my first thought in Einstein!"
```

### 4. Try Interactive Mode

For a more natural experience:

```bash
einstein
```

This starts interactive mode where you can use commands like:
- `add: your thought here`
- `search: coffee meetings`
- `list 10`
- `help`

## Essential Commands

| Command | Description | Example |
|---------|-------------|---------|
| `einstein` | Start interactive mode | `einstein` |
| `einstein auth login` | Login to server | `einstein auth login` |
| `einstein thoughts add "text"` | Add a thought | `einstein thoughts add "Great meeting today"` |
| `einstein search "query"` | Search thoughts | `einstein search "coffee meetings"` |
| `einstein thoughts list` | List recent thoughts | `einstein thoughts list` |
| `einstein config show` | Show configuration | `einstein config show` |
| `einstein help guide` | Show help guides | `einstein help guide getting-started` |

## Interactive Mode

Interactive mode is perfect for daily use:

```bash
$ einstein
🧠 Welcome to Einstein Interactive Mode

einstein> add: Had a productive day working on the CLI
✓ Added thought: abc12345...

einstein> search: productive work
🔍 Found 3 thoughts matching "productive work":
1. [abc12345] Had a productive day working on the CLI
   ...

einstein> help
# Shows available commands

einstein> exit
👋 Thanks for using Einstein!
```

## Configuration

Einstein stores configuration in platform-specific locations:

- **Linux/Unix**: `~/.config/einstein/config.toml`
- **macOS**: `~/Library/Application Support/einstein/config.toml`
- **Windows**: `%APPDATA%\einstein\config.toml`

Key settings:

```bash
# Server configuration
einstein config set api.url "https://your-server.com"
einstein config set api.timeout 30

# Output preferences
einstein config set output.colors true
einstein config set output.max_results 20

# Caching
einstein config set cache.enabled true
einstein config set cache.max_size_mb 100
```

## Shell Integration

### Install Completions

Run the installation script to set up shell completions:

```bash
./scripts/install_completions.sh
```

This installs:
- Tab completion for your shell (Bash, Zsh, Fish)
- Man page (`man einstein`)
- Suggested aliases

### Useful Aliases

Add these to your shell config file:

```bash
alias ft='einstein thoughts'
alias fs='einstein search'
alias fc='einstein config'
alias fa='einstein auth'
alias fi='einstein interactive'
```

## Common Workflows

### Daily Journaling

```bash
# Start interactive mode
einstein

# Add thoughts throughout the day
einstein> add: Morning standup went well, discussed new features
einstein> add: Lunch with Sarah, great discussion about UX design
einstein> add: Afternoon coding session, implemented search filters

# Review your day
einstein> search: today insights
einstein> list 10
```

### Research and Note-Taking

```bash
# Capture research findings
einstein thoughts add "Paper: 'Attention Is All You Need' - transformer architecture breakthrough" --tags research,ml

# Link related concepts
einstein search "transformer architecture" --tags research

# Organize by topics
einstein thoughts add "Meeting notes: AI team discussion on model architecture" --tags meetings,ai
```

### Project Documentation

```bash
# Document project decisions
einstein thoughts add "Decision: Using FastAPI for the backend API" --tags project,backend

# Track progress
einstein thoughts add "Milestone: User authentication system completed" --tags project,milestone

# Review project history
einstein search "project decisions" --tags project
```

## Getting Help

Einstein has comprehensive help built-in:

```bash
# General help
einstein --help

# Command-specific help
einstein thoughts --help
einstein search --help

# Interactive tutorial
einstein help tutorial

# Detailed guides
einstein help guide getting-started
einstein help guide commands
einstein help guide interactive
einstein help guide configuration
einstein help guide scripting
einstein help guide troubleshooting
einstein help guide examples

# Quick reference
einstein help shortcuts
einstein help workflows
```

## Troubleshooting

### Common Issues

**Connection Problems:**
```bash
# Check configuration
einstein config get api.url

# Test with verbose output
einstein --verbose auth status

# Try different URL
einstein --api-url http://localhost:8001 auth status
```

**Authentication Issues:**
```bash
# Check login status
einstein auth status

# Re-login
einstein auth logout
einstein auth login
```

**Configuration Problems:**
```bash
# Show current config
einstein config show

# Reset to defaults
einstein config reset

# Check config file location
einstein config path
```

### Debug Mode

Use verbose output for troubleshooting:

```bash
einstein --verbose <command>
```

## Next Steps

1. **Explore Interactive Mode**: Run `einstein` and try the natural command syntax
2. **Set Up Shell Integration**: Run `./scripts/install_completions.sh`
3. **Read the Guides**: Check `einstein help guide` for detailed documentation
4. **Customize Configuration**: Adjust settings with `einstein config set`
5. **Try Scripting**: Use `--json` flag for automation

## Advanced Features

### JSON Output for Scripting

```bash
# Get structured data
einstein --json thoughts list | jq '.thoughts[].content'

# Process search results
einstein --json search "AI" | jq '.results[] | select(.score > 0.8)'
```

### Environment Variables

```bash
export FARADAY_API_URL="https://my-server.com"
export FARADAY_CONFIG="/path/to/config.toml"
export FARADAY_NO_INTERACTIVE=1
```

### Multiple Configurations

```bash
# Development config
einstein --config ~/.einstein/dev.toml thoughts list

# Production config
einstein --config ~/.einstein/prod.toml thoughts list
```

You're now ready to start building your personal knowledge base with Einstein CLI! 🚀

For more detailed information, check out the comprehensive guides:
- [CLI Usage Guide](CLI_USAGE.md)
- [Configuration Guide](CONFIGURATION.md)
- Built-in help: `einstein help guide`