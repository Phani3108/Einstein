"""Search commands for Einstein CLI."""

import click
import asyncio
from typing import Optional
from datetime import datetime, timedelta

from einstein_cli.api import APIClient, APIError, AuthenticationError, NetworkError
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter


def parse_date_filter(date_str: str) -> datetime:
    """Parse date string into datetime object.
    
    Args:
        date_str: Date string in various formats (YYYY-MM-DD, today, yesterday, etc.)
        
    Returns:
        Parsed datetime object
        
    Raises:
        ValueError: If date format is invalid
    """
    date_str = date_str.lower().strip()
    
    # Handle relative dates
    if date_str == "today":
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "yesterday":
        return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str.endswith("d") or date_str.endswith("days"):
        # Handle "7d" or "7days" format
        try:
            days = int(date_str.rstrip("days").rstrip("d"))
            return (datetime.now() - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            pass
    elif date_str.endswith("w") or date_str.endswith("weeks"):
        # Handle "2w" or "2weeks" format
        try:
            weeks = int(date_str.rstrip("weeks").rstrip("w"))
            return (datetime.now() - timedelta(weeks=weeks)).replace(hour=0, minute=0, second=0, microsecond=0)
        except ValueError:
            pass
    
    # Try to parse as ISO date format
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    
    # Try common date formats
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Invalid date format: {date_str}")


@click.command()
@click.argument("query")
@click.option("--limit", default=20, help="Maximum number of results to return")
@click.option("--mood", help="Filter results by mood")
@click.option("--tags", help="Filter results by tags (comma-separated)")
@click.option("--since", help="Filter results since date (YYYY-MM-DD, today, yesterday, 7d, 2w)")
@click.option("--until", help="Filter results until date (YYYY-MM-DD, today, yesterday, 7d, 2w)")
@click.option("--min-score", type=float, help="Minimum relevance score (0.0-1.0)")
@click.option("--sort", type=click.Choice(["relevance", "date", "date-desc"]), default="relevance", 
              help="Sort results by relevance or date")
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    limit: int,
    mood: Optional[str],
    tags: Optional[str],
    since: Optional[str],
    until: Optional[str],
    min_score: Optional[float],
    sort: str,
) -> None:
    """Search thoughts using natural language queries.

    Performs semantic search through your thoughts to find relevant content
    based on meaning and context, not just keyword matching.

    Examples:
        einstein search "coffee meetings"
        einstein search "AI projects" --limit 10
        einstein search "work discussions" --mood excited --tags work
        einstein search "collaboration ideas" --since 7d --until today
        einstein search "machine learning" --min-score 0.8 --sort date
    """
    # Use cached API client if available, otherwise fall back to regular API client
    cached_api: Optional[CachedAPIClient] = ctx.obj.get("cached_api")
    api_client: APIClient = ctx.obj["api_client"]
    auth_manager: AuthManager = ctx.obj["auth_manager"]
    output: OutputFormatter = ctx.obj["output"]

    # Check authentication (skip for offline mode)
    if cached_api and cached_api.is_offline:
        # In offline mode, we can search cached thoughts without authentication
        pass
    elif not auth_manager.is_authenticated():
        output.format_error(
            "You must be logged in to search thoughts. Run 'einstein auth login'",
            "Authentication Error",
        )
        ctx.exit(1)

    # Validate query
    if not query.strip():
        output.format_error(
            "Search query cannot be empty",
            "Validation Error",
        )
        ctx.exit(1)

    # Build filters dictionary
    filters = {}
    
    if mood:
        filters["mood"] = mood
        
    if tags:
        # Split tags and clean them
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if tag_list:
            filters["tags"] = tag_list
    
    # Parse date filters
    try:
        if since:
            since_date = parse_date_filter(since)
            filters["since"] = since_date.isoformat()
            
        if until:
            until_date = parse_date_filter(until)
            filters["until"] = until_date.isoformat()
            
    except ValueError as e:
        output.format_error(str(e), "Date Format Error")
        ctx.exit(1)
    
    # Validate date range
    if since and until:
        try:
            since_dt = parse_date_filter(since)
            until_dt = parse_date_filter(until)
            if since_dt > until_dt:
                output.format_error(
                    "Since date cannot be after until date",
                    "Validation Error",
                )
                ctx.exit(1)
        except ValueError:
            pass  # Already handled above
    
    # Add other filters
    if min_score is not None:
        if not 0.0 <= min_score <= 1.0:
            output.format_error(
                "Minimum score must be between 0.0 and 1.0",
                "Validation Error",
            )
            ctx.exit(1)
        filters["min_score"] = min_score
    
    if sort != "relevance":
        filters["sort"] = sort

    async def do_search():
        try:
            # Use cached API client if available
            client = cached_api if cached_api else api_client
            
            # Show progress for search operation
            search_text = "Searching thoughts..."
            if cached_api and cached_api.is_offline:
                search_text = "Searching cached thoughts..."
            
            with output.create_progress(search_text) as progress:
                task = progress.add_task("Searching...", total=None)
                
                if cached_api:
                    # Cached API client doesn't need context manager
                    results = await client.search_thoughts(
                        query=query,
                        limit=limit,
                        filters=filters if filters else None
                    )
                else:
                    # Regular API client needs context manager
                    async with api_client:
                        results = await api_client.search_thoughts(
                            query=query,
                            limit=limit,
                            filters=filters if filters else None
                        )
                
                progress.remove_task(task)
            
            # Display results
            output.format_search_results(results)
            
            # Show cache/offline indicators
            if cached_api and cached_api.is_offline:
                output.console.print("📴 Showing cached results (offline mode)", style="yellow")
            elif cached_api and results.execution_time == 0.0:
                output.console.print("⚡ Results from cache", style="dim")
            
            # Show additional info if verbose mode
            if ctx.obj.get("verbose", False) and not output.json_mode:
                output.console.print()
                if filters:
                    output.console.print("[dim]Applied filters:[/dim]")
                    for key, value in filters.items():
                        if key == "tags" and isinstance(value, list):
                            value = ", ".join(value)
                        output.console.print(f"[dim]  {key}: {value}[/dim]")

        except AuthenticationError as e:
            output.format_error(str(e), "Authentication Error")
            ctx.exit(1)
        except NetworkError as e:
            if cached_api:
                output.format_error(f"{e} - Searching cached thoughts", "Network Error")
                try:
                    results = await cached_api.search_thoughts(query, limit, filters)
                    output.format_search_results(results)
                    output.console.print("📴 Showing cached results", style="yellow")
                except Exception:
                    ctx.exit(1)
            else:
                output.format_error(str(e), "Network Error")
                ctx.exit(1)
        except APIError as e:
            output.format_error(str(e), "API Error")
            ctx.exit(1)
        except Exception as e:
            output.format_error(f"Unexpected error: {e}", "Error")
            ctx.exit(1)

    asyncio.run(do_search())


# Create a command group for potential future search-related commands
@click.group(name="search", invoke_without_command=True)
@click.pass_context
def search_group(ctx: click.Context) -> None:
    """Search and discovery commands."""
    if ctx.invoked_subcommand is None:
        # If no subcommand, show help
        click.echo(ctx.get_help())


# Add the main search command to the group
search_group.add_command(search, name="query")

# Also make search available as a standalone command for convenience
search_command = search