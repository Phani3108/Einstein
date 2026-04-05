"""Sync command for manual synchronization."""

import click
import asyncio
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.api import NetworkError, APIError


@click.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force sync even if there are no pending operations"
)
@click.option(
    "--stats",
    is_flag=True,
    help="Show cache statistics after sync"
)
@click.pass_context
def sync(ctx, force: bool, stats: bool):
    """Sync local cache with server.
    
    This command synchronizes any pending local changes with the server,
    resolves conflicts, and updates the local cache with server data.
    """
    console = Console()
    cached_api: CachedAPIClient = ctx.obj["cached_api"]
    
    # Check if we're in offline mode
    if cached_api.is_offline:
        console.print("❌ Cannot sync while in offline mode", style="red")
        console.print("💡 Check your network connection and try again")
        return
    
    # Get cache stats before sync
    cache_stats = cached_api.get_cache_stats()
    pending_ops = cache_stats.get("pending_operations", 0)
    
    if not force and pending_ops == 0:
        console.print("✅ No pending operations to sync", style="green")
        if stats:
            _show_cache_stats(console, cache_stats)
        return
    
    console.print(f"🔄 Starting sync with {pending_ops} pending operations...")
    
    async def do_sync():
        # Progress tracking
        progress_messages = []
        
        def progress_callback(message: str):
            progress_messages.append(message)
        
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True
            ) as progress:
                
                task = progress.add_task("Syncing...", total=None)
                
                # Perform sync
                sync_results = await cached_api.sync(progress_callback)
                
                progress.update(task, completed=True)
            
            # Display sync results
            _show_sync_results(console, sync_results)
            
            # Show cache stats if requested
            if stats:
                updated_stats = cached_api.get_cache_stats()
                _show_cache_stats(console, updated_stats)
        
        except NetworkError as e:
            console.print(f"❌ Network error during sync: {e}", style="red")
            console.print("💡 Check your network connection and try again")
        
        except APIError as e:
            console.print(f"❌ API error during sync: {e}", style="red")
            console.print("💡 Check your authentication and server status")
        
        except Exception as e:
            console.print(f"❌ Unexpected error during sync: {e}", style="red")
            console.print("💡 Please report this issue if it persists")
    
    asyncio.run(do_sync())


def _show_sync_results(console: Console, results: dict):
    """Display sync results in a formatted table.
    
    Args:
        console: Rich console for output
        results: Sync results dictionary
    """
    # Create results table
    table = Table(title="Sync Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    
    table.add_row("Operations Processed", str(results.get("operations_processed", 0)))
    table.add_row("Operations Failed", str(results.get("operations_failed", 0)))
    table.add_row("Conflicts Resolved", str(results.get("conflicts_resolved", 0)))
    
    console.print(table)
    
    # Show errors if any
    errors = results.get("errors", [])
    if errors:
        console.print("\n⚠️  Errors encountered during sync:", style="yellow")
        for error in errors[:5]:  # Show first 5 errors
            console.print(f"  • {error}", style="red")
        
        if len(errors) > 5:
            console.print(f"  ... and {len(errors) - 5} more errors", style="red")
    
    # Success message
    if results.get("operations_processed", 0) > 0:
        console.print(f"\n✅ Successfully synced {results['operations_processed']} operations", style="green")
    
    if results.get("operations_failed", 0) == 0 and not errors:
        console.print("🎉 Sync completed without errors!", style="green")


def _show_cache_stats(console: Console, stats: dict):
    """Display cache statistics.
    
    Args:
        console: Rich console for output
        stats: Cache statistics dictionary
    """
    # Create stats table
    table = Table(title="Cache Statistics", show_header=True, header_style="bold blue")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="white")
    
    table.add_row("Cached Thoughts", str(stats.get("cached_thoughts", 0)))
    table.add_row("Dirty Thoughts", str(stats.get("dirty_thoughts", 0)))
    table.add_row("Cached Searches", str(stats.get("cached_searches", 0)))
    table.add_row("Pending Operations", str(stats.get("pending_operations", 0)))
    table.add_row("Cache Size", f"{stats.get('cache_size_mb', 0):.2f} MB")
    table.add_row("Offline Mode", "Yes" if stats.get("offline_mode", False) else "No")
    
    console.print(table)
    
    # Show cache path
    cache_path = stats.get("cache_path", "Unknown")
    console.print(f"\n📁 Cache location: {cache_path}", style="dim")


@click.command()
@click.option(
    "--clear",
    is_flag=True,
    help="Clear all cached data"
)
@click.pass_context
def cache(ctx, clear: bool):
    """Manage local cache.
    
    View cache statistics or clear cached data.
    """
    console = Console()
    cached_api: CachedAPIClient = ctx.obj["cached_api"]
    
    if clear:
        # Ask for confirmation before clearing
        if click.confirm("Are you sure you want to clear the cache?"):
            try:
                cached_api.clear_cache()
                console.print("✅ Cache cleared successfully", style="green")
            except Exception as e:
                console.print(f"❌ Error clearing cache: {e}", style="red")
        else:
            console.print("Cache clear cancelled", style="yellow")
    else:
        # Show cache statistics
        stats = cached_api.get_cache_stats()
        _show_cache_stats(console, stats)


@click.command()
@click.option(
    "--offline",
    is_flag=True,
    help="Enable offline mode"
)
@click.option(
    "--online",
    is_flag=True,
    help="Disable offline mode"
)
@click.pass_context
def mode(ctx, offline: bool, online: bool):
    """Switch between online and offline modes.
    
    In offline mode, all operations work with local cache only.
    In online mode, operations try to sync with server.
    """
    console = Console()
    cached_api: CachedAPIClient = ctx.obj["cached_api"]
    
    if offline and online:
        console.print("❌ Cannot specify both --offline and --online", style="red")
        return
    
    if offline:
        cached_api.set_offline_mode(True)
        console.print("📴 Switched to offline mode", style="yellow")
        console.print("💡 All operations will use local cache only")
    
    elif online:
        cached_api.set_offline_mode(False)
        console.print("🌐 Switched to online mode", style="green")
        console.print("💡 Operations will sync with server when possible")
    
    else:
        # Show current mode
        current_mode = "offline" if cached_api.is_offline else "online"
        mode_icon = "📴" if cached_api.is_offline else "🌐"
        console.print(f"{mode_icon} Currently in {current_mode} mode")
        
        # Show cache stats
        stats = cached_api.get_cache_stats()
        pending = stats.get("pending_operations", 0)
        if pending > 0:
            console.print(f"⏳ {pending} operations pending sync", style="yellow")


# Group commands together
@click.group()
def sync_group():
    """Cache and synchronization commands."""
    pass


sync_group.add_command(sync)
sync_group.add_command(cache)
sync_group.add_command(mode)