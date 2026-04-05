"""Help and tutorial commands for Einstein CLI."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.markdown import Markdown
from typing import Optional, Dict, List

from einstein_cli.output import OutputFormatter


@click.group(name="help")
def help_group() -> None:
    """Help and tutorial commands."""
    pass


@help_group.command()
@click.argument("topic", required=False)
@click.pass_context
def guide(ctx: click.Context, topic: Optional[str]) -> None:
    """Show detailed help guides for specific topics.
    
    \b
    AVAILABLE TOPICS:
      getting-started    # First-time setup and basic usage
      commands          # Complete command reference
      interactive       # Interactive mode guide
      configuration     # Configuration management
      scripting         # Automation and scripting
      troubleshooting   # Common issues and solutions
      examples          # Real-world usage examples
    
    \b
    EXAMPLES:
      einstein help guide                    # List all available topics
      einstein help guide getting-started   # Show getting started guide
      einstein help guide commands          # Show command reference
    """
    output: OutputFormatter = ctx.obj["output"]
    
    guides = {
        "getting-started": _show_getting_started_guide,
        "commands": _show_commands_guide,
        "interactive": _show_interactive_guide,
        "configuration": _show_configuration_guide,
        "scripting": _show_scripting_guide,
        "troubleshooting": _show_troubleshooting_guide,
        "examples": _show_examples_guide,
    }
    
    if not topic:
        _show_guide_index(output)
    elif topic in guides:
        guides[topic](output)
    else:
        output.format_error(
            f"Unknown help topic: {topic}",
            "Help Error"
        )
        output.console.print("\nAvailable topics:")
        for guide_topic in guides.keys():
            output.console.print(f"  • {guide_topic}")


@help_group.command()
@click.pass_context
def tutorial(ctx: click.Context) -> None:
    """Start an interactive tutorial for new users.
    
    This command provides a step-by-step walkthrough of Einstein CLI
    features, perfect for first-time users.
    
    \b
    TUTORIAL COVERS:
      • Initial configuration setup
      • Authentication and login
      • Adding and managing thoughts
      • Searching your knowledge base
      • Using interactive mode
      • Advanced features and tips
    
    \b
    EXAMPLES:
      einstein help tutorial    # Start the interactive tutorial
    """
    output: OutputFormatter = ctx.obj["output"]
    _run_interactive_tutorial(ctx, output)


@help_group.command()
@click.pass_context
def shortcuts(ctx: click.Context) -> None:
    """Show keyboard shortcuts and quick commands.
    
    \b
    EXAMPLES:
      einstein help shortcuts    # Show all shortcuts and aliases
    """
    output: OutputFormatter = ctx.obj["output"]
    _show_shortcuts_guide(output)


@help_group.command()
@click.pass_context
def workflows(ctx: click.Context) -> None:
    """Show common workflows and usage patterns.
    
    \b
    EXAMPLES:
      einstein help workflows    # Show common usage patterns
    """
    output: OutputFormatter = ctx.obj["output"]
    _show_workflows_guide(output)


def _show_guide_index(output: OutputFormatter) -> None:
    """Show the index of available help guides."""
    output.console.print(Panel(
        "[bold blue]📚 Einstein CLI Help Center[/bold blue]\n\n"
        "Welcome to the comprehensive help system! Choose a topic below to get detailed guidance.",
        title="Help Center",
        border_style="blue"
    ))
    
    guides_table = Table(title="Available Help Topics")
    guides_table.add_column("Topic", style="cyan", no_wrap=True)
    guides_table.add_column("Description", style="white")
    guides_table.add_column("Best For", style="dim")
    
    guides_info = [
        ("getting-started", "First-time setup and basic usage", "New users"),
        ("commands", "Complete command reference", "All users"),
        ("interactive", "Interactive mode guide", "Daily users"),
        ("configuration", "Configuration management", "Power users"),
        ("scripting", "Automation and scripting", "Developers"),
        ("troubleshooting", "Common issues and solutions", "Problem solving"),
        ("examples", "Real-world usage examples", "Learning by example"),
    ]
    
    for topic, description, best_for in guides_info:
        guides_table.add_row(topic, description, best_for)
    
    output.console.print(guides_table)
    
    output.console.print("\n[bold]Quick Commands:[/bold]")
    output.console.print("  [cyan]einstein help guide getting-started[/cyan]  # Start here if you're new")
    output.console.print("  [cyan]einstein help tutorial[/cyan]               # Interactive walkthrough")
    output.console.print("  [cyan]einstein help shortcuts[/cyan]              # Keyboard shortcuts")
    output.console.print("  [cyan]einstein help workflows[/cyan]              # Common usage patterns")


def _show_getting_started_guide(output: OutputFormatter) -> None:
    """Show the getting started guide."""
    guide_content = """
# 🚀 Getting Started with Einstein CLI

Welcome to Einstein! This guide will help you set up and start using the CLI in just a few minutes.

## Step 1: Initial Configuration

First, configure your Einstein server URL:

```bash
einstein config set api.url http://localhost:8001
```

For production servers, use your actual server URL:
```bash
einstein config set api.url https://your-einstein-server.com
```

## Step 2: Authentication

Login to your Einstein account:

```bash
einstein auth login
```

You'll be prompted for your email and password. The CLI will securely store your authentication token.

## Step 3: Verify Setup

Check that everything is working:

```bash
einstein auth status
```

You should see a confirmation that you're logged in.

## Step 4: Add Your First Thought

Create your first thought:

```bash
einstein thoughts add "This is my first thought in Einstein!"
```

## Step 5: Try Interactive Mode

For a more conversational experience, try interactive mode:

```bash
einstein
```

This starts an interactive session where you can use natural commands like:
- `add: your thought here`
- `search: coffee meetings`
- `list 10`

## Step 6: Explore Commands

Try these essential commands:

```bash
# List your recent thoughts
einstein thoughts list

# Search for thoughts
einstein search "first thought"

# Get help on any command
einstein thoughts --help
```

## Next Steps

- Run `einstein help tutorial` for an interactive walkthrough
- Check `einstein help guide commands` for complete command reference
- Explore `einstein help guide interactive` for interactive mode tips

You're all set! Start capturing your thoughts and building your personal knowledge base.
"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Getting Started Guide",
        border_style="green"
    ))


def _show_commands_guide(output: OutputFormatter) -> None:
    """Show the complete commands reference."""
    output.console.print(Panel(
        "[bold blue]📋 Complete Command Reference[/bold blue]",
        title="Commands Guide",
        border_style="blue"
    ))
    
    # Main command groups
    groups_table = Table(title="Command Groups")
    groups_table.add_column("Group", style="cyan", no_wrap=True)
    groups_table.add_column("Purpose", style="white")
    groups_table.add_column("Key Commands", style="dim")
    
    groups_info = [
        ("auth", "Authentication management", "login, logout, status"),
        ("config", "Configuration settings", "get, set, show, reset"),
        ("thoughts", "Thought management", "add, list, show, delete"),
        ("search", "Semantic search", "query with filters"),
        ("sync", "Cache synchronization", "sync, status"),
        ("help", "Help and tutorials", "guide, tutorial, shortcuts"),
    ]
    
    for group, purpose, commands in groups_info:
        groups_table.add_row(group, purpose, commands)
    
    output.console.print(groups_table)
    
    # Global options
    output.console.print("\n[bold]Global Options (work with any command):[/bold]")
    global_options = [
        ("--config PATH", "Use custom configuration file"),
        ("--api-url URL", "Override API server URL"),
        ("--json", "Output in JSON format for scripting"),
        ("--verbose", "Enable detailed output for debugging"),
        ("--no-interactive", "Disable automatic interactive mode"),
    ]
    
    for option, description in global_options:
        output.console.print(f"  [cyan]{option:<20}[/cyan] {description}")
    
    # Quick reference
    output.console.print("\n[bold]Quick Reference:[/bold]")
    quick_commands = [
        ("einstein", "Start interactive mode"),
        ("einstein auth login", "Login to server"),
        ("einstein thoughts add \"text\"", "Add a new thought"),
        ("einstein search \"query\"", "Search thoughts"),
        ("einstein thoughts list", "List recent thoughts"),
        ("einstein config show", "Show all settings"),
        ("einstein --help", "Show main help"),
    ]
    
    for command, description in quick_commands:
        output.console.print(f"  [green]{command:<30}[/green] {description}")


def _show_interactive_guide(output: OutputFormatter) -> None:
    """Show the interactive mode guide."""
    guide_content = """
# 🎯 Interactive Mode Guide

Interactive mode provides a conversational interface for daily Einstein usage.

## Starting Interactive Mode

```bash
einstein                    # Auto-starts if no command given
einstein interactive        # Explicit interactive mode
```

## Interactive Commands

| Command | Description | Example |
|---------|-------------|---------|
| `add: content` | Add a thought | `add: Had a great meeting` |
| `search: query` | Search thoughts | `search: coffee meetings` |
| `list [N]` | List thoughts | `list 10` |
| `show ID` | Show thought details | `show abc123` |
| `delete ID` | Delete a thought | `delete abc123` |
| `sync` | Sync with server | `sync` |
| `stats` | Show statistics | `stats` |
| `config` | Show configuration | `config` |
| `help` | Show help | `help` |
| `history` | Command history | `history` |
| `clear` | Clear screen | `clear` |
| `exit` | Exit interactive mode | `exit` or `quit` |

## Tips and Tricks

### Natural Syntax
Use colon syntax for natural commands:
```
einstein> add: This is a natural way to add thoughts
einstein> search: find my coffee-related thoughts
```

### Command Shortcuts
- `h` → `help`
- `q` → `quit`
- `ls` → `list`
- `rm` → `delete`
- `?` → `help`

### Navigation
- **Ctrl+C**: Cancel current input (doesn't exit)
- **Ctrl+D** or **EOF**: Exit interactive mode
- **Up/Down arrows**: Command history (if supported by terminal)

### Context Awareness
Interactive mode remembers your session and provides:
- Command history with `history` command
- Persistent authentication status
- Smart error handling and suggestions

## Customization

Control interactive mode behavior:

```bash
# Disable auto-interactive mode
einstein config set ui.auto_interactive false

# Use environment variable
export EINSTEIN_NO_INTERACTIVE=1

# One-time disable
einstein --no-interactive
```

## Best Practices

1. **Daily Workflow**: Use interactive mode for regular thought capture
2. **Batch Operations**: Use CLI mode for scripting and automation
3. **Exploration**: Use `help` command to discover features
4. **Efficiency**: Learn shortcuts for frequently used commands

Interactive mode is perfect for daily journaling, quick searches, and exploring your thoughts!
"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Interactive Mode Guide",
        border_style="magenta"
    ))


def _show_configuration_guide(output: OutputFormatter) -> None:
    """Show the configuration guide."""
    guide_content = """
# ⚙️ Configuration Guide

Einstein CLI uses TOML configuration files for settings management.

## Configuration Location

The CLI automatically uses platform-appropriate locations:

- **Windows**: `%APPDATA%\\einstein\\config.toml`
- **macOS**: `~/Library/Application Support/einstein/config.toml`
- **Linux**: `~/.config/einstein/config.toml`

## Essential Commands

```bash
einstein config show              # View all settings
einstein config get api.url       # Get specific setting
einstein config set api.url URL   # Set a value
einstein config reset             # Reset to defaults
einstein config path              # Show config file location
```

## Key Configuration Sections

### API Settings
```bash
einstein config set api.url "http://localhost:8001"
einstein config set api.timeout 30
```

### Authentication
```bash
einstein config set auth.auto_login true
einstein config set auth.remember_token true
```

### Output Formatting
```bash
einstein config set output.colors true
einstein config set output.max_results 20
einstein config set output.pager "auto"
```

### Caching
```bash
einstein config set cache.enabled true
einstein config set cache.max_size_mb 100
einstein config set cache.sync_interval 300
```

## Environment-Specific Configs

### Development
```bash
einstein --config ~/.einstein/dev.toml config show
```

### Production
```bash
einstein --config ~/.einstein/prod.toml config show
```

## Validation

All configuration values are validated:
- **Booleans**: `true`, `false`
- **Numbers**: Valid integers/floats within allowed ranges
- **Strings**: Any text value
- **URLs**: Must be valid HTTP/HTTPS URLs

## Troubleshooting

```bash
# Check current config
einstein config show

# Verify config file location
einstein config path

# Reset corrupted config
einstein config reset

# Use temporary config
einstein --config /tmp/test.toml config show
```

See the full configuration documentation for complete details!
"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Configuration Guide",
        border_style="yellow"
    ))


def _show_scripting_guide(output: OutputFormatter) -> None:
    """Show the scripting and automation guide."""
    guide_content = """
# 🤖 Scripting and Automation Guide

Einstein CLI is designed for both interactive use and automation.

## JSON Output Mode

Use `--json` flag for machine-readable output:

```bash
# Get structured data
einstein --json thoughts list | jq '.thoughts[].content'

# Search with processing
einstein --json search "AI" | jq '.results[] | select(.score > 0.8)'

# Configuration as JSON
einstein --json config show | jq '.api.url'
```

## Environment Variables

Control CLI behavior in scripts:

```bash
export EINSTEIN_API_URL="https://my-server.com"
export EINSTEIN_CONFIG="/path/to/config.toml"
export EINSTEIN_NO_INTERACTIVE=1
```

## Bash Scripting Examples

### Daily Backup Script
```bash
#!/bin/bash
# backup_thoughts.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="$HOME/einstein-backups"
mkdir -p "$BACKUP_DIR"

echo "Backing up thoughts for $DATE..."
einstein --json thoughts list --limit 10000 > "$BACKUP_DIR/thoughts_$DATE.json"

if [ $? -eq 0 ]; then
    echo "✅ Backup completed: $BACKUP_DIR/thoughts_$DATE.json"
else
    echo "❌ Backup failed"
    exit 1
fi
```

### Bulk Import Script
```bash
#!/bin/bash
# import_notes.sh

while IFS= read -r line; do
    if [ -n "$line" ]; then
        echo "Adding: $line"
        einstein thoughts add "$line"
        sleep 0.5  # Rate limiting
    fi
done < notes.txt
## Python Integration

```python
#!/usr/bin/env python3
import subprocess
import json
import sys
from datetime import datetime

def einstein_command(cmd_args, json_output=True):
    \"\"\"Execute einstein command and return result.\"\"\"
    cmd = ['einstein']
    if json_output:
        cmd.append('--json')
    cmd.extend(cmd_args)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        return json.loads(result.stdout) if json_output else result.stdout
    else:
        raise Exception(f"Command failed: {result.stderr}")

# Usage examples
def search_and_analyze(query):
    \"\"\"Search thoughts and analyze results.\"\"\"
    results = einstein_command(['search', query])
    
    print(f"Found {len(results['results'])} thoughts")
    for thought in results['results']:
        print(f"- {thought['content'][:50]}... (score: {thought['score']:.2f})")

def daily_stats():
    \"\"\"Get daily thought statistics.\"\"\"
    thoughts = einstein_command(['thoughts', 'list', '--limit', '1000'])
    
    today = datetime.now().date()
    today_thoughts = [
        t for t in thoughts['thoughts'] 
        if datetime.fromisoformat(t['created_at']).date() == today
    ]
    
    print(f"Thoughts added today: {len(today_thoughts)}")
    return len(today_thoughts)

if __name__ == "__main__":
    search_and_analyze("machine learning")
    daily_stats()
```

## Cron Jobs

```bash
# Add to crontab (crontab -e)

# Daily backup at 2 AM
0 2 * * * /path/to/backup_thoughts.sh >> /var/log/einstein-backup.log 2>&1

# Weekly summary email
0 9 * * 1 einstein --json search "weekly goals" | mail -s "Weekly Goals" user@example.com
```

## Error Handling

```bash
#!/bin/bash
# robust_script.sh

set -e  # Exit on error

# Function to handle errors
handle_error() {
    echo "❌ Error on line $1"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Check authentication
if ! einstein auth status > /dev/null 2>&1; then
    echo "❌ Not authenticated. Please run: einstein auth login"
    exit 1
fi

# Your script logic here
einstein thoughts add "Automated thought from script"
echo "✅ Script completed successfully"
```

## Best Practices

1. **Always use `--json`** for parsing output
2. **Check exit codes** for error handling
3. **Use environment variables** for configuration
4. **Implement rate limiting** for bulk operations
5. **Validate authentication** before operations
6. **Log operations** for debugging
7. **Use structured error handling**

Happy automating! 🚀"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Scripting Guide",
        border_style="cyan"
    ))


def _show_troubleshooting_guide(output: OutputFormatter) -> None:
    """Show the troubleshooting guide."""
    guide_content = """
# 🔧 Troubleshooting Guide

Common issues and their solutions.

## Connection Issues

### Problem: "Connection refused" or "Network error"

**Causes:**
- Einstein server is not running
- Wrong API URL configured
- Network connectivity issues

**Solutions:**
```bash
# Check current API URL
einstein config get api.url

# Test server connectivity
curl -I $(einstein config get api.url)

# Try different URL
einstein --api-url http://localhost:8001 auth status

# Check server logs
# (depends on your server setup)
```

### Problem: "SSL/TLS errors"

**Solutions:**
```bash
# For development servers with self-signed certificates
export PYTHONHTTPSVERIFY=0  # NOT recommended for production

# Use HTTP instead of HTTPS for local development
einstein config set api.url "http://localhost:8001"
```

## Authentication Issues

### Problem: "Authentication failed" or "Invalid credentials"

**Solutions:**
```bash
# Clear stored tokens and re-login
einstein auth logout
einstein auth login

# Check authentication status
einstein auth status

# Verify server URL is correct
einstein config get api.url
```

### Problem: "Token expired" errors

**Solutions:**
```bash
# Re-authenticate
einstein auth login

# Check token expiration
einstein auth status

# Enable automatic token refresh (if available)
einstein config set auth.auto_login true
```

## Configuration Issues

### Problem: "Configuration key not found"

**Solutions:**
```bash
# Check available configuration keys
einstein config show

# Reset corrupted configuration
einstein config reset

# Use correct key format (dot notation)
einstein config set api.url "http://localhost:8001"  # Correct
einstein config set api_url "http://localhost:8001"   # Wrong
```

### Problem: "Permission denied" on config file

**Solutions:**
```bash
# Check config file location
einstein config path

# Fix permissions (Unix/Linux/macOS)
chmod 644 ~/.config/einstein/config.toml
chmod 755 ~/.config/einstein/

# Use alternative config location
einstein --config ~/my-einstein-config.toml config show
```

## Performance Issues

### Problem: Slow search or command responses

**Solutions:**
```bash
# Enable caching
einstein config set cache.enabled true

# Increase cache size
einstein config set cache.max_size_mb 200

# Reduce sync frequency
einstein config set cache.sync_interval 600

# Use verbose mode to identify bottlenecks
einstein --verbose search "query"
```

### Problem: High memory usage

**Solutions:**
```bash
# Reduce cache size
einstein config set cache.max_size_mb 50

# Disable caching if not needed
einstein config set cache.enabled false

# Limit result counts
einstein config set output.max_results 10
```

## Interactive Mode Issues

### Problem: Interactive mode doesn't start

**Solutions:**
```bash
# Force interactive mode
einstein interactive

# Check auto-interactive setting
einstein config get ui.auto_interactive

# Enable auto-interactive mode
einstein config set ui.auto_interactive true

# Check environment variables
echo $EINSTEIN_NO_INTERACTIVE  # Should be empty
```

### Problem: Commands not working in interactive mode

**Solutions:**
- Use colon syntax: `add: your thought`
- Check command spelling and syntax
- Use `help` command for available commands
- Try `clear` to reset the session

## Data Issues

### Problem: "Thought not found" errors

**Solutions:**
```bash
# Sync with server
einstein sync

# Check thought ID format
einstein thoughts list  # Get correct IDs

# Search instead of direct access
einstein search "partial content"
```

### Problem: Sync conflicts or cache issues

**Solutions:**
```bash
# Force sync
einstein sync --force

# Clear cache
einstein cache clear

# Disable cache temporarily
einstein --no-cache thoughts list
```

## Debug Mode

Enable verbose output for detailed debugging:

```bash
# Verbose mode shows detailed information
einstein --verbose <command>

# JSON output for structured debugging
einstein --json <command>

# Combine for maximum detail
einstein --verbose --json <command>
```

## Getting Help

If you're still having issues:

1. **Check the logs** (if available)
2. **Try with verbose output**: `einstein --verbose <command>`
3. **Test with minimal config**: `einstein config reset`
4. **Verify server status** independently
5. **Check network connectivity**
6. **Review configuration**: `einstein config show`

## Common Error Messages

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| Connection refused | Server not running | Check server status |
| Authentication failed | Wrong credentials | `einstein auth login` |
| Configuration key not found | Typo in key name | Check with `config show` |
| Permission denied | File permissions | Fix file permissions |
| Invalid JSON | Malformed response | Check server status |
| Command not found | Typo in command | Use `--help` for correct syntax |

Most issues can be resolved by checking configuration, authentication status, and server connectivity! 🔍
"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Troubleshooting Guide",
        border_style="red"
    ))


def _show_examples_guide(output: OutputFormatter) -> None:
    """Show real-world usage examples."""
    guide_content = """
# 💡 Real-World Usage Examples

Practical examples of how to use Einstein CLI in different scenarios.

## Daily Journaling Workflow

```bash
# Morning routine - capture thoughts
einstein thoughts add "Goals for today: finish project proposal, team meeting at 2pm"

# Throughout the day - quick captures
einstein thoughts add "Great insight from Sarah about user experience design"
einstein thoughts add "Book recommendation: 'Atomic Habits' - seems relevant to productivity"

# Evening review - search and reflect
einstein search "today goals" --since today
einstein search "insights" --limit 5
```

## Research and Note-Taking

```bash
# Capture research notes with metadata
einstein thoughts add "Machine learning paper: attention mechanisms improve translation quality" --tags research,ml,papers

# Organize by topics
einstein thoughts add "Meeting notes: discussed new product features" --tags meetings,product

# Find related information
einstein search "machine learning attention" --tags research
einstein search "product features" --tags meetings
```

## Team Collaboration

```bash
# Share insights with team (using JSON output)
einstein --json search "best practices" | jq '.results[] | {content, score}' > team_insights.json

# Capture meeting outcomes
einstein thoughts add "Team decided to use React for frontend, concerns about learning curve addressed"

# Track action items
einstein thoughts add "ACTION: Research React training options by Friday" --tags action,urgent
```

## Content Creation

```bash
# Capture ideas for blog posts
einstein thoughts add "Blog idea: How semantic search changes personal knowledge management"

# Collect quotes and references
einstein thoughts add "Quote from Einstein: 'Information is not knowledge' - relevant for AI discussion"

# Find related content when writing
einstein search "knowledge management" --limit 10
einstein search "AI discussion quotes"
```

## Learning and Development

```bash
# Track learning progress
einstein thoughts add "Completed Python async/await tutorial - key insight: use asyncio.gather for concurrent operations"

# Capture book highlights
einstein thoughts add "From 'Deep Work': 'The ability to focus without distraction on cognitively demanding tasks is becoming increasingly valuable'"

# Review learning over time
einstein search "tutorial completed" --since 30d
einstein search "book highlights" --tags learning
```

## Project Management

```bash
# Track project ideas
einstein thoughts add "Project idea: CLI tool for semantic search of personal notes" --tags project,idea

# Document decisions
einstein thoughts add "Decided to use Click framework for CLI - good documentation and rich features"

# Monitor progress
einstein search "project progress" --since 7d
einstein thoughts add "Project milestone: basic CLI structure completed"
```

## Creative Writing

```bash
# Capture story ideas
einstein thoughts add "Story idea: AI that helps people find lost memories through semantic search"

# Character development
einstein thoughts add "Character: Dr. Sarah Chen, memory researcher, struggles with her own forgotten childhood"

# Find inspiration
einstein search "story ideas" --tags creative
einstein search "character development"
```

## Business Intelligence

```bash
# Track market insights
einstein thoughts add "Market trend: increasing demand for privacy-focused AI tools" --tags market,trends

# Competitive analysis
einstein thoughts add "Competitor analysis: NotionAI focuses on writing assistance, opportunity in research tools"

# Strategic planning
einstein search "market trends" --since 90d
einstein search "opportunities" --tags strategy
```

## Automation Examples

### Daily Summary Script
```bash
#!/bin/bash
# daily_summary.sh

echo "📊 Daily Einstein Summary for $(date +%Y-%m-%d)"
echo "================================================"

# Count today's thoughts
TODAY_COUNT=$(einstein --json thoughts list --since today | jq '.thoughts | length')
echo "Thoughts added today: $TODAY_COUNT"

# Show top themes
echo -e "\n🏷️ Top themes today:"
einstein --json search "today" --limit 20 | jq -r '.results[].tags[]?' | sort | uniq -c | sort -nr | head -5

# Show most relevant thoughts
echo -e "\n💭 Most relevant thoughts:"
einstein search "important insights" --since today --limit 3
```

### Weekly Review Script
```bash
#!/bin/bash
# weekly_review.sh

echo "📈 Weekly Einstein Review"
echo "======================="

# Weekly stats
WEEK_COUNT=$(einstein --json thoughts list --since 7d | jq '.thoughts | length')
echo "Thoughts this week: $WEEK_COUNT"

# Key themes
echo -e "\n🎯 Key themes this week:"
einstein search "goals achievements progress" --since 7d --limit 5

# Action items
echo -e "\n✅ Action items:"
einstein search "action todo" --since 7d --limit 10
```

## Advanced Search Patterns

```bash
# Find thoughts by mood and timeframe
einstein search "creative ideas" --mood excited --since 30d

# Complex topic searches
einstein search "machine learning AND productivity" --limit 15

# Find thoughts with specific patterns
einstein search "learned today" --since 7d
einstein search "question:" --limit 20  # Find all questions you've captured

# Discover connections
einstein search "similar to yesterday's meeting insights"
```

## Configuration for Different Contexts

### Work Configuration
```bash
# Work profile setup
einstein --config ~/.einstein/work.toml config set api.url "https://work-einstein.company.com"
einstein --config ~/.einstein/work.toml config set output.max_results 50

# Work alias
alias fwork="einstein --config ~/.einstein/work.toml"
```

### Personal Configuration
```bash
# Personal profile setup
einstein --config ~/.einstein/personal.toml config set api.url "http://localhost:8001"
einstein --config ~/.einstein/personal.toml config set cache.max_size_mb 200

# Personal alias
alias fpersonal="einstein --config ~/.einstein/personal.toml"
```

These examples show how Einstein CLI can adapt to various workflows and use cases. The key is to develop consistent patterns that work for your specific needs! 🎯
"""
    
    output.console.print(Panel(
        Markdown(guide_content),
        title="Usage Examples",
        border_style="green"
    ))


def _show_shortcuts_guide(output: OutputFormatter) -> None:
    """Show keyboard shortcuts and quick commands."""
    output.console.print(Panel(
        "[bold blue]⌨️ Shortcuts and Quick Commands[/bold blue]",
        title="Shortcuts Guide",
        border_style="blue"
    ))
    
    # Command aliases
    aliases_table = Table(title="Command Aliases")
    aliases_table.add_column("Alias", style="cyan", no_wrap=True)
    aliases_table.add_column("Full Command", style="white")
    aliases_table.add_column("Context", style="dim")
    
    aliases_info = [
        ("h", "help", "Interactive mode"),
        ("q", "quit", "Interactive mode"),
        ("ls", "list", "Interactive mode"),
        ("rm", "delete", "Interactive mode"),
        ("?", "help", "Interactive mode"),
        ("-v", "--verbose", "Global option"),
        ("-j", "--json", "Global option (if implemented)"),
    ]
    
    for alias, full_command, context in aliases_info:
        aliases_table.add_row(alias, full_command, context)
    
    output.console.print(aliases_table)
    
    # Keyboard shortcuts
    output.console.print("\n[bold]Keyboard Shortcuts (Interactive Mode):[/bold]")
    shortcuts = [
        ("Ctrl+C", "Cancel current input (doesn't exit)"),
        ("Ctrl+D", "Exit interactive mode"),
        ("Tab", "Command completion (if supported)"),
        ("↑/↓", "Command history navigation (terminal dependent)"),
        ("Ctrl+L", "Clear screen (terminal shortcut)"),
    ]
    
    for shortcut, description in shortcuts:
        output.console.print(f"  [cyan]{shortcut:<12}[/cyan] {description}")
    
    # Quick command patterns
    output.console.print("\n[bold]Quick Command Patterns:[/bold]")
    patterns = [
        ("add: text", "Natural thought addition"),
        ("search: query", "Natural search syntax"),
        ("list N", "List N thoughts"),
        ("show ID", "Show thought details"),
        ("config key", "Get config value"),
    ]
    
    for pattern, description in patterns:
        output.console.print(f"  [green]{pattern:<15}[/green] {description}")
    
    # Shell aliases suggestions
    output.console.print("\n[bold]Suggested Shell Aliases:[/bold]")
    shell_aliases = [
        ("alias ft='einstein thoughts'", "Quick thought commands"),
        ("alias fs='einstein search'", "Quick search"),
        ("alias fc='einstein config'", "Quick config"),
        ("alias fa='einstein auth'", "Quick auth"),
        ("alias fi='einstein interactive'", "Start interactive mode"),
    ]
    
    for alias_cmd, description in shell_aliases:
        output.console.print(f"  [yellow]{alias_cmd:<35}[/yellow] {description}")
    
    output.console.print("\n[dim]Add these aliases to your ~/.bashrc or ~/.zshrc for faster access![/dim]")


def _show_workflows_guide(output: OutputFormatter) -> None:
    """Show common workflows and usage patterns."""
    output.console.print(Panel(
        "[bold blue]🔄 Common Workflows and Usage Patterns[/bold blue]",
        title="Workflows Guide",
        border_style="blue"
    ))
    
    workflows = [
        {
            "name": "Daily Capture Workflow",
            "description": "Efficient daily thought capture and review",
            "steps": [
                "Start interactive mode: `einstein`",
                "Quick captures: `add: thought content`",
                "Batch review: `list 20`",
                "Search recent: `search: today insights`",
                "Exit: `exit`"
            ]
        },
        {
            "name": "Research Session Workflow",
            "description": "Structured research and note-taking",
            "steps": [
                "Set context: `einstein thoughts add \"Starting research on [topic]\"`",
                "Capture findings: `einstein thoughts add \"Key insight: ...\" --tags research`",
                "Link ideas: `einstein search \"related concepts\"`",
                "Summarize: `einstein thoughts add \"Research summary: ...\"`"
            ]
        },
        {
            "name": "Weekly Review Workflow",
            "description": "Periodic review and analysis",
            "steps": [
                "Review week: `einstein search \"\" --since 7d`",
                "Find patterns: `einstein search \"goals progress achievements\"`",
                "Plan ahead: `einstein thoughts add \"Next week focus: ...\"`",
                "Archive insights: Export important findings"
            ]
        },
        {
            "name": "Project Documentation Workflow",
            "description": "Document project progress and decisions",
            "steps": [
                "Project start: `einstein thoughts add \"Project [name] kickoff\" --tags project`",
                "Log decisions: `einstein thoughts add \"Decision: ...\" --tags project,decision`",
                "Track progress: `einstein thoughts add \"Milestone: ...\" --tags project,milestone`",
                "Review project: `einstein search \"project [name]\" --tags project`"
            ]
        }
    ]
    
    for workflow in workflows:
        output.console.print(f"\n[bold cyan]{workflow['name']}[/bold cyan]")
        output.console.print(f"[dim]{workflow['description']}[/dim]")
        
        for i, step in enumerate(workflow['steps'], 1):
            output.console.print(f"  {i}. {step}")
    
    # Usage patterns
    output.console.print(f"\n[bold]Usage Patterns by Role:[/bold]")
    
    roles_table = Table()
    roles_table.add_column("Role", style="cyan", no_wrap=True)
    roles_table.add_column("Primary Use Cases", style="white")
    roles_table.add_column("Key Commands", style="dim")
    
    roles_info = [
        ("Researcher", "Literature review, hypothesis tracking", "search, add --tags research"),
        ("Developer", "Code insights, learning notes", "add --tags code, search \"bug solution\""),
        ("Writer", "Idea capture, inspiration tracking", "add: story idea, search \"character\""),
        ("Manager", "Meeting notes, decision tracking", "add --tags meeting, search \"decisions\""),
        ("Student", "Study notes, concept linking", "add --tags study, search \"concept\""),
        ("Entrepreneur", "Market insights, opportunity tracking", "add --tags market, search \"opportunity\""),
    ]
    
    for role, use_cases, commands in roles_info:
        roles_table.add_row(role, use_cases, commands)
    
    output.console.print(roles_table)


def _run_interactive_tutorial(ctx: click.Context, output: OutputFormatter) -> None:
    """Run an interactive tutorial for new users."""
    from rich.prompt import Prompt, Confirm
    
    output.console.print(Panel(
        "[bold blue]🎓 Welcome to the Einstein CLI Interactive Tutorial![/bold blue]\n\n"
        "This tutorial will guide you through the essential features of Einstein CLI.\n"
        "You can exit at any time by pressing Ctrl+C.",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    try:
        # Step 1: Introduction
        if not Confirm.ask("Ready to start the tutorial?", default=True, console=output.console):
            output.console.print("Tutorial cancelled. Run `einstein help tutorial` anytime to restart!")
            return
        
        # Step 2: Configuration check
        output.console.print("\n[bold]Step 1: Configuration Check[/bold]")
        output.console.print("Let's check your current configuration...")
        
        config = ctx.obj["config"]
        api_url = config.get("api.url", "http://localhost:8001")
        output.console.print(f"Current API URL: [cyan]{api_url}[/cyan]")
        
        if not Confirm.ask("Is this the correct server URL?", default=True, console=output.console):
            new_url = Prompt.ask("Enter your Einstein server URL", console=output.console)
            config.set("api.url", new_url)
            output.console.print(f"✅ Updated API URL to: [cyan]{new_url}[/cyan]")
        
        # Step 3: Authentication check
        output.console.print("\n[bold]Step 2: Authentication Check[/bold]")
        auth_manager = ctx.obj["auth_manager"]
        
        if auth_manager.is_authenticated():
            output.console.print("✅ You're already logged in!")
        else:
            output.console.print("❌ You're not logged in.")
            if Confirm.ask("Would you like to login now?", default=True, console=output.console):
                output.console.print("Please run: [cyan]einstein auth login[/cyan]")
                output.console.print("Then restart the tutorial with: [cyan]einstein help tutorial[/cyan]")
                return
        
        # Step 4: Basic commands demo
        output.console.print("\n[bold]Step 3: Basic Commands[/bold]")
        output.console.print("Let's explore the main commands you'll use daily:")
        
        commands_demo = [
            ("einstein thoughts add \"text\"", "Add a new thought"),
            ("einstein search \"query\"", "Search your thoughts"),
            ("einstein thoughts list", "List recent thoughts"),
            ("einstein", "Start interactive mode"),
        ]
        
        for command, description in commands_demo:
            output.console.print(f"  [green]{command:<30}[/green] {description}")
        
        if Confirm.ask("Would you like to try adding a test thought?", default=True, console=output.console):
            test_content = Prompt.ask(
                "Enter a test thought (or press Enter for default)", 
                default="This is my first thought in Einstein CLI!",
                console=output.console
            )
            
            # Simulate adding a thought (we won't actually do it in the tutorial)
            output.console.print(f"You would run: [cyan]einstein thoughts add \"{test_content}\"[/cyan]")
            output.console.print("✅ This would add your thought to Einstein!")
        
        # Step 5: Interactive mode demo
        output.console.print("\n[bold]Step 4: Interactive Mode[/bold]")
        output.console.print("Interactive mode provides a conversational interface:")
        
        interactive_commands = [
            ("add: your thought here", "Natural thought addition"),
            ("search: coffee meetings", "Natural search"),
            ("list 10", "List recent thoughts"),
            ("help", "Show available commands"),
            ("exit", "Exit interactive mode"),
        ]
        
        for command, description in interactive_commands:
            output.console.print(f"  [magenta]{command:<25}[/magenta] {description}")
        
        # Step 6: Configuration tips
        output.console.print("\n[bold]Step 5: Configuration Tips[/bold]")
        output.console.print("Useful configuration commands:")
        
        config_tips = [
            ("einstein config show", "View all settings"),
            ("einstein config set output.colors true", "Enable colors"),
            ("einstein config set cache.enabled true", "Enable caching"),
            ("einstein config reset", "Reset to defaults"),
        ]
        
        for command, description in config_tips:
            output.console.print(f"  [yellow]{command:<35}[/yellow] {description}")
        
        # Step 7: Next steps
        output.console.print("\n[bold]Step 6: Next Steps[/bold]")
        output.console.print("Now you're ready to use Einstein CLI! Here's what to do next:")
        
        next_steps = [
            "Try interactive mode: `einstein`",
            "Add your first real thought: `einstein thoughts add \"your thought\"`",
            "Explore help guides: `einstein help guide`",
            "Check out examples: `einstein help guide examples`",
            "Set up shell aliases for faster access",
        ]
        
        for i, step in enumerate(next_steps, 1):
            output.console.print(f"  {i}. {step}")
        
        # Tutorial completion
        output.console.print("\n[bold green]🎉 Tutorial Complete![/bold green]")
        output.console.print("You now know the basics of Einstein CLI. Happy thought capturing!")
        
        if Confirm.ask("Would you like to see the quick reference?", default=True, console=output.console):
            _show_quick_reference(output)
            
    except KeyboardInterrupt:
        output.console.print("\n\n[yellow]Tutorial interrupted. You can restart anytime with:[/yellow]")
        output.console.print("[cyan]einstein help tutorial[/cyan]")
    except Exception as e:
        output.console.print(f"\n[red]Tutorial error: {e}[/red]")
        output.console.print("Please try again or check `einstein help guide getting-started`")


def _show_quick_reference(output: OutputFormatter) -> None:
    """Show a quick reference card."""
    output.console.print(Panel(
        """[bold]Essential Commands:[/bold]
[green]einstein[/green]                          Start interactive mode
[green]einstein auth login[/green]               Login to server
[green]einstein thoughts add "text"[/green]      Add a thought
[green]einstein search "query"[/green]           Search thoughts
[green]einstein thoughts list[/green]            List recent thoughts
[green]einstein config show[/green]              Show configuration
[green]einstein help guide[/green]               Show help guides

[bold]Interactive Mode:[/bold]
[magenta]add: your thought[/magenta]             Add thought naturally
[magenta]search: your query[/magenta]           Search naturally
[magenta]list 10[/magenta]                      List thoughts
[magenta]help[/magenta]                         Show help
[magenta]exit[/magenta]                         Exit interactive mode

[bold]Global Options:[/bold]
[cyan]--json[/cyan]                         JSON output for scripts
[cyan]--verbose[/cyan]                      Detailed output
[cyan]--config PATH[/cyan]                 Custom config file
[cyan]--api-url URL[/cyan]                 Override server URL""",
        title="Quick Reference",
        border_style="green"
    ))