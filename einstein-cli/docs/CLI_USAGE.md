# Einstein CLI Usage Guide

Complete guide to using the Einstein CLI for managing your personal semantic engine.

## Quick Start

The Einstein CLI provides two modes of operation:

### Smart Interactive Mode (Default)
When you run `einstein` without any commands in a terminal, it automatically starts interactive mode for a conversational experience:

```bash
einstein
# 💡 Starting interactive mode. Use --help to see all commands or --no-interactive to disable.
# 
# ╭───────────────────────────────────────────────────────────────────────────────────────────╮
# │ 🧠 Welcome to Einstein Interactive Mode                                                    │
# ╰────────────────── Type 'help' for available commands or 'exit' to quit ───────────────────╯
# 
# einstein> add: Had a great meeting today
# ✓ Added thought: abc12345...
# einstein> search: meetings
# 🔍 Search results...
# einstein> exit
```

### Standard CLI Mode
Use specific commands for scripting, automation, or one-off operations:

```bash
einstein thoughts add "Quick thought"
einstein search "important meetings" --limit 5
einstein thoughts list | grep "urgent"
```

## Controlling Interactive Mode

The CLI intelligently detects when to use interactive mode, but you have full control:

### Disable Interactive Mode
```bash
# One-time disable
einstein --no-interactive

# Environment variable
export FARADAY_NO_INTERACTIVE=1
einstein

# Configuration setting
einstein config set ui.auto_interactive false
```

### Force Interactive Mode
```bash
# Always starts interactive mode
einstein interactive
```

### Auto-Detection Rules
Interactive mode starts automatically when:
- ✅ No specific command given (just `einstein`)
- ✅ Running in a terminal (not piped/redirected)
- ✅ Not requesting JSON output (`--json`)
- ✅ Not in CI environment
- ✅ Not disabled via flag, environment, or config

## Table of Contents

- [Getting Started](#getting-started)
- [Global Options](#global-options)
- [Configuration Commands](#configuration-commands)
- [Authentication Commands](#authentication-commands)
- [Thought Management Commands](#thought-management-commands)
- [Output Formats](#output-formats)
- [Advanced Usage](#advanced-usage)
- [Scripting and Automation](#scripting-and-automation)
- [Troubleshooting](#troubleshooting)

## Getting Started

### First-Time Setup

1. **Install the CLI** (when available on PyPI):
   ```bash
   pip install einstein-cli
   ```

2. **Configure your server**:
   ```bash
   einstein config set api.url http://localhost:8001
   ```

3. **Login to your account**:
   ```bash
   einstein auth login
   ```

4. **Verify setup**:
   ```bash
   einstein auth status
   ```

### Quick Commands Reference

```bash
# Configuration
einstein config show                    # View all settings
einstein config set api.url <url>       # Set server URL
einstein config reset                   # Reset to defaults

# Authentication  
einstein auth login                     # Login to server
einstein auth status                    # Check login status
einstein auth logout                    # Logout

# Thoughts
einstein thoughts add "content"         # Add new thought
einstein thoughts search "query"        # Search thoughts
einstein thoughts list                  # List recent thoughts
einstein thoughts get <id>              # Get specific thought

# Utility
einstein version                        # Show version
einstein --help                         # Show help
```

## Global Options

These options can be used with any command:

### `--config PATH`

Use a custom configuration file:

```bash
# Use development config
einstein --config ~/dev-config.toml thoughts list

# Use production config
einstein --config /etc/einstein/prod.toml auth status
```

### `--api-url URL`

Override the configured API URL:

```bash
# Connect to different server temporarily
einstein --api-url http://staging.example.com:8001 thoughts list

# Test against local development server
einstein --api-url http://localhost:3000 auth status
```

### `--json`

Output results in JSON format:

```bash
# Get configuration as JSON
einstein --json config show

# Search with JSON output for processing
einstein --json thoughts search "coffee" | jq '.results[].content'

# Get structured data for scripts
einstein --json thoughts list | jq '.thoughts | length'
```

### `--verbose`

Enable verbose output for debugging:

```bash
# Debug connection issues
einstein --verbose thoughts list

# See detailed API requests
einstein --verbose auth login
```

## Configuration Commands

The `einstein config` command group manages CLI settings.

### `einstein config show`

Display all configuration settings in a readable format:

```bash
$ einstein config show
Current Configuration:

api:
  api.url = http://localhost:8001
  api.timeout = 30
auth:
  auth.auto_login = True
  auth.remember_token = True
output:
  output.colors = True
  output.pager = auto
  output.max_results = 20
cache:
  cache.enabled = True
  cache.max_size_mb = 100
  cache.sync_interval = 300
```

### `einstein config get [KEY]`

Get specific configuration value or all values:

```bash
# Get specific value
$ einstein config get api.url
api.url = http://localhost:8001

# Get all values (same as 'show')
$ einstein config get
# ... shows all configuration
```

### `einstein config set KEY VALUE`

Set configuration values with automatic type detection:

```bash
# String values
einstein config set api.url "https://my-server.com"

# Boolean values (JSON parsing)
einstein config set output.colors true
einstein config set auth.auto_login false

# Numeric values
einstein config set api.timeout 60
einstein config set cache.max_size_mb 200

# Complex values (JSON)
einstein config set custom.list '[1, 2, 3]'
```

### `einstein config reset`

Reset all configuration to defaults with confirmation:

```bash
$ einstein config reset
Are you sure you want to reset all configuration to defaults? [y/N]: y
✅ Configuration reset to defaults
```

### `einstein config path`

Show the location of the configuration file:

```bash
$ einstein config path
Configuration file: /Users/username/Library/Application Support/einstein/config.toml
✓ File exists
```

## Authentication Commands

The `einstein auth` command group manages authentication.

### `einstein auth login`

Login to your Einstein server:

```bash
$ einstein auth login
Username: john@example.com
Password: [hidden]
✅ Successfully logged in as john@example.com
```

**Interactive prompts**:
- Username/email
- Password (hidden input)
- Optional: Remember credentials

### `einstein auth status`

Check current authentication status:

```bash
$ einstein auth status
✅ Logged in as john@example.com
Server: http://localhost:8001
Token expires: 2024-01-15 14:30:00 UTC
```

### `einstein auth logout`

Logout and clear stored tokens:

```bash
$ einstein auth logout
✅ Successfully logged out
```

## Thought Management Commands

The `einstein thoughts` command group manages your thoughts.

### `einstein thoughts add CONTENT`

Add a new thought:

```bash
# Simple thought
einstein thoughts add "Had a great meeting with the design team today"

# Thought with quotes
einstein thoughts add "Einstein said: 'Imagination is more important than knowledge'"

# Multi-line thought (use quotes)
einstein thoughts add "Project ideas:
1. AI-powered note taking
2. Semantic search for documents
3. Personal knowledge graph"
```

**Response**:
```bash
✅ Thought added successfully
ID: abc123def456
Content: Had a great meeting with the design team today
```

### `einstein thoughts search QUERY`

Search your thoughts using natural language:

```bash
# Simple search
einstein thoughts search "design meetings"

# Complex queries
einstein thoughts search "AI projects and machine learning"
einstein thoughts search "book recommendations fiction"

# Search with filters (if supported)
einstein thoughts search "coffee" --limit 10
```

**Response**:
```bash
Found 3 thoughts matching "design meetings":

1. [abc123] Had a great meeting with the design team today
   Similarity: 0.95 | Created: 2024-01-10 14:30

2. [def456] Design review went well, team loved the new mockups  
   Similarity: 0.87 | Created: 2024-01-08 10:15

3. [ghi789] Planning next design sprint meeting for Friday
   Similarity: 0.82 | Created: 2024-01-05 16:45
```

### `einstein thoughts list`

List recent thoughts:

```bash
# List default number of thoughts
einstein thoughts list

# List specific number
einstein thoughts list --limit 50

# List with different sorting
einstein thoughts list --sort created_desc
einstein thoughts list --sort relevance
```

**Response**:
```bash
Recent thoughts (20 most recent):

1. [abc123] Had a great meeting with the design team today
   Created: 2024-01-10 14:30

2. [def456] Learning about vector databases and embeddings
   Created: 2024-01-10 09:15

3. [ghi789] Coffee shop idea: AI-powered menu recommendations
   Created: 2024-01-09 16:20
```

### `einstein thoughts get ID`

Get a specific thought by ID:

```bash
einstein thoughts get abc123def456
```

**Response**:
```bash
Thought Details:

ID: abc123def456
Content: Had a great meeting with the design team today
Created: 2024-01-10 14:30:00 UTC
Updated: 2024-01-10 14:30:00 UTC
Tags: meeting, design, team
Related: 3 similar thoughts found
```

## Output Formats

### Human-Readable Output (Default)

Designed for terminal use with colors, formatting, and visual elements:

```bash
$ einstein thoughts search "coffee"
Found 2 thoughts matching "coffee":

☕ [abc123] Great coffee shop downtown with amazing wifi
   Similarity: 0.92 | Created: 2024-01-10 14:30

☕ [def456] Coffee meeting with Sarah went really well  
   Similarity: 0.85 | Created: 2024-01-08 10:15
```

### JSON Output

Structured data perfect for scripting and processing:

```bash
$ einstein --json thoughts search "coffee"
{
  "query": "coffee",
  "results": [
    {
      "id": "abc123",
      "content": "Great coffee shop downtown with amazing wifi",
      "similarity": 0.92,
      "created_at": "2024-01-10T14:30:00Z",
      "tags": ["coffee", "location", "wifi"]
    },
    {
      "id": "def456", 
      "content": "Coffee meeting with Sarah went really well",
      "similarity": 0.85,
      "created_at": "2024-01-08T10:15:00Z",
      "tags": ["coffee", "meeting", "sarah"]
    }
  ],
  "total": 2,
  "query_time": 0.045
}
```

## Advanced Usage

### Combining Commands with Pipes

```bash
# Search and get details of first result
einstein --json thoughts search "AI" | jq -r '.results[0].id' | xargs einstein thoughts get

# Count thoughts by tag
einstein --json thoughts list --limit 1000 | jq '.thoughts[].tags[]' | sort | uniq -c

# Export all thoughts to file
einstein --json thoughts list --limit 10000 > my_thoughts_backup.json
```

### Environment Variables

Set environment variables for common configurations:

```bash
# Set default API URL
export FARADAY_API_URL="https://my-server.com"

# Set default config file
export FARADAY_CONFIG="$HOME/.config/einstein/prod.toml"

# Use in commands
einstein thoughts list
```

### Aliases and Shortcuts

Create shell aliases for common operations:

```bash
# Add to your ~/.bashrc or ~/.zshrc
alias ft="einstein thoughts"
alias fc="einstein config"
alias fa="einstein auth"

# Usage
ft add "Quick thought"
ft search "important"
fc show
fa status
```

### Configuration Profiles

Manage multiple environments:

```bash
# Development profile
alias einstein-dev="einstein --config ~/.config/einstein/dev.toml"

# Production profile  
alias einstein-prod="einstein --config ~/.config/einstein/prod.toml"

# Staging profile
alias einstein-staging="einstein --config ~/.config/einstein/staging.toml"

# Usage
einstein-dev thoughts add "Development note"
einstein-prod thoughts search "production issues"
```

## Scripting and Automation

### Bash Scripts

```bash
#!/bin/bash
# daily_thoughts.sh - Add daily standup notes

echo "Adding daily standup thoughts..."

# Add thoughts from command line arguments
for thought in "$@"; do
    echo "Adding: $thought"
    einstein thoughts add "$thought"
done

# Search for today's thoughts
echo "Today's thoughts:"
einstein thoughts search "$(date +%Y-%m-%d)"
```

### Python Integration

```python
#!/usr/bin/env python3
import subprocess
import json
import sys

def search_thoughts(query):
    """Search thoughts and return JSON results."""
    result = subprocess.run([
        'einstein', '--json', 'thoughts', 'search', query
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout)
    else:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None

def add_thought(content):
    """Add a new thought."""
    result = subprocess.run([
        'einstein', 'thoughts', 'add', content
    ], capture_output=True, text=True)
    
    return result.returncode == 0

# Usage
if __name__ == "__main__":
    # Search for thoughts
    results = search_thoughts("machine learning")
    if results:
        print(f"Found {len(results['results'])} thoughts")
        
    # Add new thought
    if add_thought("Automated thought from Python script"):
        print("Thought added successfully")
```

### Cron Jobs

```bash
# Add to crontab (crontab -e)

# Daily backup of thoughts
0 2 * * * einstein --json thoughts list --limit 10000 > ~/backups/thoughts_$(date +\%Y\%m\%d).json

# Weekly summary
0 9 * * 1 einstein thoughts search "weekly goals" | mail -s "Weekly Goals" user@example.com
```

## Troubleshooting

### Common Issues

#### Connection Problems

```bash
# Check configuration
einstein config get api.url

# Test connection with verbose output
einstein --verbose auth status

# Try different URL
einstein --api-url http://localhost:8001 auth status
```

#### Authentication Issues

```bash
# Check login status
einstein auth status

# Clear and re-login
einstein auth logout
einstein auth login

# Check server connectivity
curl -I $(einstein config get api.url)
```

#### Configuration Problems

```bash
# Check config file location and contents
einstein config path
einstein config show

# Reset corrupted configuration
einstein config reset

# Use temporary config
einstein --config /tmp/test-config.toml config show
```

### Debug Mode

Enable verbose output for detailed debugging:

```bash
# See all HTTP requests and responses
einstein --verbose thoughts search "debug"

# Check configuration loading
einstein --verbose config show

# Debug authentication flow
einstein --verbose auth login
```

### Error Messages

Common error messages and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Server not running | Check server status and URL |
| `Authentication failed` | Invalid credentials | Re-login with correct credentials |
| `Configuration key not found` | Typo in key name | Check available keys with `config show` |
| `Invalid configuration value` | Wrong data type | Check value format and type |
| `Permission denied` | File permissions | Fix config file permissions |

### Getting Help

```bash
# General help
einstein --help

# Command-specific help
einstein config --help
einstein thoughts --help
einstein auth --help

# Subcommand help
einstein thoughts add --help
einstein config set --help
```

### Reporting Issues

When reporting issues, include:

1. **CLI version**: `einstein version`
2. **Configuration**: `einstein --json config show` (remove sensitive data)
3. **Error output**: Full error message with `--verbose` flag
4. **Environment**: OS, terminal, shell version
5. **Steps to reproduce**: Exact commands that cause the issue

This comprehensive usage guide should help users effectively use all aspects of the Einstein CLI.