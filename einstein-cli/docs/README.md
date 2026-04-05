# Einstein CLI Documentation

Welcome to the Einstein CLI documentation! This directory contains comprehensive guides for using the Einstein command-line interface.

## Documentation Index

### 📖 [CLI Usage Guide](CLI_USAGE.md)
Complete guide to using all Einstein CLI commands, including:
- Getting started and first-time setup
- All command groups (config, auth, thoughts)
- Output formats and global options
- Advanced usage patterns and scripting
- Troubleshooting common issues

### ⚙️ [Configuration Guide](CONFIGURATION.md)
Detailed configuration management documentation:
- Platform-specific configuration paths
- All configuration options and their meanings
- Configuration validation and error handling
- Environment-specific setups
- Security considerations

## Quick Reference

### Essential Commands

```bash
# Setup
einstein config set api.url http://localhost:8001
einstein auth login

# Daily usage
einstein thoughts add "Your thought here"
einstein thoughts search "search query"
einstein thoughts list

# Configuration
einstein config show
einstein config set key value
einstein config reset
```

### Global Options

```bash
--config PATH     # Use custom config file
--api-url URL     # Override API URL
--json           # JSON output format
--verbose        # Verbose output
```

## Getting Help

- **Command help**: `einstein --help` or `einstein <command> --help`
- **Configuration**: `einstein config --help`
- **Version info**: `einstein version`

## Additional Resources

- **Main README**: [../README.md](../README.md) - Project overview and installation
- **Contributing**: See main repository for contribution guidelines
- **Issues**: Report bugs and feature requests in the main repository

## Documentation Structure

```
docs/
├── README.md           # This file - documentation index
├── CLI_USAGE.md        # Complete CLI usage guide
└── CONFIGURATION.md    # Configuration management guide
```

Each guide is self-contained and can be read independently, though they cross-reference each other where relevant.