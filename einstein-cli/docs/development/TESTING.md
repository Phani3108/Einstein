# Testing the Einstein CLI

This document explains how to test the Einstein CLI against a running server.

## Prerequisites

1. **Einstein Server Running**: You need a Einstein server running on `http://localhost:8001`
2. **User Account**: You need a valid user account on the server
3. **CLI Installed**: The CLI should be installed via Poetry

## Manual Testing

### 1. Check CLI Installation

```bash
cd einstein-cli
poetry run einstein --help
```

### 2. Test Configuration

```bash
# Show current configuration
poetry run einstein config show

# Set API URL (if different from default)
poetry run einstein config set api.url http://localhost:8001

# Test JSON output
poetry run einstein --json config show
```

### 3. Test Authentication

```bash
# Check authentication status (should show not authenticated)
poetry run einstein auth status

# Login (will prompt for email and password)
poetry run einstein auth login

# Check status again (should show authenticated)
poetry run einstein auth status

# Test JSON output
poetry run einstein --json auth status
```

### 4. Test Thought Management

```bash
# Add a thought
poetry run einstein thoughts add "This is my first test thought"

# Add a thought with metadata
poetry run einstein thoughts add "Working on the CLI" --mood excited --tags work,cli

# List thoughts
poetry run einstein thoughts list

# List with filters
poetry run einstein thoughts list --mood excited --limit 5

# Show specific thought (replace ID with actual ID from list)
poetry run einstein thoughts show <thought-id>

# Test JSON output
poetry run einstein --json thoughts list
```

### 5. Test Error Handling

```bash
# Try to access thoughts without authentication (after logout)
poetry run einstein auth logout
poetry run einstein thoughts list  # Should show authentication error

# Try to connect to non-existent server
poetry run einstein --api-url http://localhost:9999 auth status
```

## Automated Testing

Run the integration test script:

```bash
cd einstein-cli
python test_cli_integration.py
```

This script will:
1. Test server connectivity
2. Test JSON output mode
3. Test authentication flow
4. Test thought CRUD operations
5. Test logout functionality

## Expected Behavior

### Authentication Flow
- ✅ `einstein auth status` shows "Not authenticated" initially
- ✅ `einstein auth login` prompts for email/password
- ✅ After successful login, `einstein auth status` shows "Authenticated"
- ✅ Commands requiring auth work after login
- ✅ `einstein auth logout` clears authentication

### Thought Management
- ✅ `einstein thoughts add` creates new thoughts
- ✅ `einstein thoughts list` shows recent thoughts
- ✅ `einstein thoughts show <id>` displays specific thought
- ✅ Metadata (mood, tags) is properly handled
- ✅ Filtering works (by mood, tags, etc.)

### Error Handling
- ✅ Network errors are handled gracefully
- ✅ Authentication errors show helpful messages
- ✅ Validation errors are displayed clearly
- ✅ Commands requiring auth check authentication first

### Output Formatting
- ✅ Rich formatting works in normal mode
- ✅ JSON output works with `--json` flag
- ✅ Error messages are properly formatted
- ✅ Success messages are clear and informative

## Troubleshooting

### Connection Issues
- Ensure the Einstein server is running on the correct port
- Check firewall settings
- Verify the API URL in configuration

### Authentication Issues
- Ensure you have a valid user account on the server
- Check that the server's authentication endpoint is working
- Verify token storage permissions (should be 600)

### Command Issues
- Run with `--verbose` flag for more detailed output
- Check the configuration with `einstein config show`
- Ensure you're in the correct directory and using Poetry

## Server Requirements

The CLI expects the server to have these endpoints:

### Authentication
- `POST /auth/token` - Login with email/password
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Logout

### Thoughts
- `GET /api/v1/thoughts` - List thoughts
- `POST /api/v1/thoughts` - Create thought
- `GET /api/v1/thoughts/{id}` - Get specific thought
- `DELETE /api/v1/thoughts/{id}` - Delete thought
- `GET /api/v1/search` - Search thoughts

### Health
- `GET /health` - Health check

The server should return JSON responses and handle JWT authentication via Bearer tokens.