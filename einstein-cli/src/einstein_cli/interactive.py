"""Interactive shell for Einstein CLI using Click's prompt utilities."""

import asyncio
import shlex
import sys
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt

from einstein_cli.config import ConfigManager
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.output import OutputFormatter
from einstein_cli.auth import AuthManager


class InteractiveSession:
    """Interactive shell session for Einstein CLI."""
    
    def __init__(
        self,
        config: ConfigManager,
        cached_api: CachedAPIClient,
        output: OutputFormatter,
        auth_manager: AuthManager,
        console: Console,
    ):
        self.config = config
        self.cached_api = cached_api
        self.output = output
        self.auth_manager = auth_manager
        self.console = console
        self.history: List[str] = []
        self.running = True
        
        # Command registry
        self.commands: Dict[str, Callable] = {
            "add": self._handle_add,
            "search": self._handle_search,
            "list": self._handle_list,
            "show": self._handle_show,
            "delete": self._handle_delete,
            "sync": self._handle_sync,
            "stats": self._handle_stats,
            "config": self._handle_config,
            "help": self._handle_help,
            "tutorial": self._handle_tutorial,
            "tips": self._handle_tips,
            "history": self._handle_history,
            "clear": self._handle_clear,
            "exit": self._handle_exit,
            "quit": self._handle_exit,
        }
        
        # Command aliases
        self.aliases = {
            "h": "help",
            "q": "quit",
            "ls": "list",
            "rm": "delete",
            "?": "help",
        }
    
    def start(self) -> None:
        """Start the interactive session."""
        self._show_welcome()
        
        try:
            while self.running:
                try:
                    # Get user input
                    prompt_text = self._get_prompt()
                    user_input = Prompt.ask(prompt_text, console=self.console)
                    
                    if not user_input.strip():
                        continue
                    
                    # Add to history
                    self.history.append(user_input)
                    
                    # Parse and execute command
                    asyncio.run(self._execute_command(user_input))
                    
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Use 'exit' or 'quit' to leave the session[/yellow]")
                    continue
                except EOFError:
                    break
                    
        except Exception as e:
            self.console.print(f"[red]Session error: {e}[/red]")
        finally:
            self._show_goodbye()
    
    def _show_welcome(self) -> None:
        """Display welcome message."""
        welcome_text = Text()
        welcome_text.append("🧠 ", style="blue")
        welcome_text.append("Welcome to Einstein Interactive Mode", style="bold blue")
        
        panel = Panel(
            welcome_text,
            subtitle="Type 'help' for available commands or 'exit' to quit",
            border_style="blue",
        )
        self.console.print(panel)
        self.console.print()
    
    def _show_goodbye(self) -> None:
        """Display goodbye message."""
        self.console.print("\n[blue]👋 Thanks for using Einstein! Your thoughts are safe.[/blue]")
    
    def _get_prompt(self) -> str:
        """Get the command prompt string."""
        if self.auth_manager.is_authenticated():
            return "[bold green]einstein>[/bold green]"
        else:
            return "[bold yellow]einstein (not logged in)>[/bold yellow]"
    
    async def _execute_command(self, user_input: str) -> None:
        """Parse and execute a command."""
        try:
            # Parse command and arguments
            parts = shlex.split(user_input)
            if not parts:
                return
            
            command = parts[0].lower()
            args = parts[1:]
            
            # Handle aliases
            command = self.aliases.get(command, command)
            
            # Handle colon syntax (e.g., "add: my thought")
            if ":" in user_input:
                colon_index = user_input.find(":")
                potential_command = user_input[:colon_index].strip().lower()
                if potential_command in ["add", "search"]:
                    command = potential_command
                    content = user_input[colon_index + 1:].strip()
                    args = [content] if content else []
            
            # Execute command
            if command in self.commands:
                await self.commands[command](args)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
                self.console.print("Type 'help' to see available commands.")
                
        except Exception as e:
            self.console.print(f"[red]Error executing command: {e}[/red]")
    
    async def _handle_add(self, args: List[str]) -> None:
        """Handle add command."""
        if not args:
            content = Prompt.ask("Enter thought content", console=self.console)
        else:
            content = " ".join(args)
        
        if not content.strip():
            self.console.print("[yellow]Cannot add empty thought[/yellow]")
            return
        
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Create thought
            thought = await self.cached_api.create_thought(content)
            thought_id = thought.id if hasattr(thought, 'id') else thought.get('id', 'unknown')
            self.console.print(f"[green]✓[/green] Added thought: {thought_id[:8]}...")
            
        except Exception as e:
            self.console.print(f"[red]Failed to add thought: {e}[/red]")
    
    async def _handle_search(self, args: List[str]) -> None:
        """Handle search command."""
        if not args:
            query = Prompt.ask("Enter search query", console=self.console)
        else:
            query = " ".join(args)
        
        if not query.strip():
            self.console.print("[yellow]Cannot search with empty query[/yellow]")
            return
        
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Perform search
            results = await self.cached_api.search_thoughts(query, limit=5)
            
            # Handle both SearchResult objects and dictionaries
            if hasattr(results, 'thoughts'):
                thoughts = results.thoughts
            else:
                thoughts = results.get("results", [])
            
            if not thoughts:
                self.console.print("[yellow]No results found[/yellow]")
                return
            
            # Display results
            self.output.format_search_results(results)
            
        except Exception as e:
            self.console.print(f"[red]Search failed: {e}[/red]")
    
    async def _handle_list(self, args: List[str]) -> None:
        """Handle list command."""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Parse limit
            limit = 10
            if args and args[0].isdigit():
                limit = int(args[0])
            
            # Get thoughts
            thoughts = await self.cached_api.get_thoughts(limit=limit)
            
            if not thoughts:
                self.console.print("[yellow]No thoughts found[/yellow]")
                return
            
            # Display thoughts
            self.output.format_thoughts_list(thoughts)
            
        except Exception as e:
            self.console.print(f"[red]Failed to list thoughts: {e}[/red]")
    
    async def _handle_show(self, args: List[str]) -> None:
        """Handle show command."""
        if not args:
            thought_id = Prompt.ask("Enter thought ID", console=self.console)
        else:
            thought_id = args[0]
        
        if not thought_id.strip():
            self.console.print("[yellow]Please provide a thought ID[/yellow]")
            return
        
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Get thought
            thought = await self.cached_api.get_thought(thought_id)
            
            if not thought:
                self.console.print(f"[red]Thought {thought_id} not found[/red]")
                return
            
            # Display thought
            self.output.format_thought_detail(thought)
            
        except Exception as e:
            self.console.print(f"[red]Failed to show thought: {e}[/red]")
    
    async def _handle_delete(self, args: List[str]) -> None:
        """Handle delete command."""
        if not args:
            thought_id = Prompt.ask("Enter thought ID", console=self.console)
        else:
            thought_id = args[0]
        
        if not thought_id.strip():
            self.console.print("[yellow]Please provide a thought ID[/yellow]")
            return
        
        # Confirm deletion
        confirm = Prompt.ask(
            f"Are you sure you want to delete thought {thought_id}?",
            choices=["y", "n"],
            default="n",
            console=self.console
        )
        
        if confirm.lower() != "y":
            self.console.print("[yellow]Deletion cancelled[/yellow]")
            return
        
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Delete thought
            await self.cached_api.delete_thought(thought_id)
            self.console.print(f"[green]✓[/green] Deleted thought {thought_id}")
            
        except Exception as e:
            self.console.print(f"[red]Failed to delete thought: {e}[/red]")
    
    async def _handle_sync(self, args: List[str]) -> None:
        """Handle sync command."""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            self.console.print("[blue]Syncing with server...[/blue]")
            await self.cached_api.sync()
            self.console.print("[green]✓[/green] Sync completed")
            
        except Exception as e:
            self.console.print(f"[red]Sync failed: {e}[/red]")
    
    async def _handle_stats(self, args: List[str]) -> None:
        """Handle stats command."""
        try:
            # Check authentication
            if not self.auth_manager.is_authenticated():
                self.console.print("[yellow]You need to login first. Use the main CLI: einstein auth login[/yellow]")
                return
            
            # Get basic stats from cache
            stats = await self.cached_api.get_stats()
            
            # Display stats
            table = Table(title="Thought Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Thoughts", str(stats.get("total_thoughts", 0)))
            table.add_row("Cached Thoughts", str(stats.get("cached_thoughts", 0)))
            table.add_row("Pending Sync", str(stats.get("pending_sync", 0)))
            
            self.console.print(table)
            
        except Exception as e:
            self.console.print(f"[red]Failed to get stats: {e}[/red]")
    
    async def _handle_config(self, args: List[str]) -> None:
        """Handle config command."""
        if not args:
            # Show current config
            config_data = {
                "API URL": str(self.config.get("api.url", "http://localhost:8001")),
                "Cache Enabled": str(self.config.get("cache.enabled", True)),
                "Output Colors": str(self.config.get("output.colors", True)),
            }
            
            table = Table(title="Configuration")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            
            for key, value in config_data.items():
                table.add_row(key, value)
            
            self.console.print(table)
        else:
            self.console.print("[yellow]Config modification not supported in interactive mode.[/yellow]")
            self.console.print("Use the main CLI: einstein config set <key> <value>")
    
    async def _handle_help(self, args: List[str]) -> None:
        """Handle help command with context-sensitive help."""
        if args and len(args) > 0:
            # Show help for specific command
            command = args[0].lower()
            await self._show_command_help(command)
        else:
            # Show general help
            await self._show_general_help()
    
    async def _show_general_help(self) -> None:
        """Show general help for interactive mode."""
        help_table = Table(title="Available Commands")
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        help_table.add_column("Example", style="dim")
        
        commands_help = [
            ("add <content>", "Add a new thought", "add: Had a great idea"),
            ("search <query>", "Search thoughts", "search: coffee meetings"),
            ("list [limit]", "List recent thoughts", "list 5"),
            ("show <id>", "Show thought details", "show abc123"),
            ("delete <id>", "Delete a thought", "delete abc123"),
            ("sync", "Sync with server", "sync"),
            ("stats", "Show statistics", "stats"),
            ("config", "Show configuration", "config"),
            ("history [limit]", "Show command history", "history 10"),
            ("clear", "Clear screen", "clear"),
            ("help [command]", "Show help (or help for specific command)", "help add"),
            ("tutorial", "Start interactive tutorial", "tutorial"),
            ("tips", "Show usage tips", "tips"),
            ("exit/quit", "Exit interactive mode", "exit"),
        ]
        
        for cmd, desc, example in commands_help:
            help_table.add_row(cmd, desc, example)
        
        self.console.print(help_table)
        
        # Show contextual tips based on authentication status
        self.console.print("\n[bold]Context-Sensitive Tips:[/bold]")
        
        if not self.auth_manager.is_authenticated():
            self.console.print("🔐 [yellow]You're not logged in.[/yellow] Use the main CLI to login:")
            self.console.print("   [cyan]einstein auth login[/cyan]")
        else:
            self.console.print("✅ [green]You're logged in and ready to go![/green]")
        
        # Show cache status
        if hasattr(self.cached_api, 'is_offline') and self.cached_api.is_offline:
            self.console.print("📴 [yellow]Currently in offline mode.[/yellow] Use 'sync' to reconnect.")
        
        self.console.print("\n[dim]General Tips:[/dim]")
        self.console.print("• Use colon syntax: 'add: your thought here'")
        self.console.print("• Press Ctrl+C to cancel current input")
        self.console.print("• Commands are case-insensitive")
        self.console.print("• Type 'help <command>' for detailed help on any command")
        self.console.print("• Type 'tutorial' for a guided walkthrough")
    
    async def _show_command_help(self, command: str) -> None:
        """Show detailed help for a specific command."""
        command_help = {
            "add": {
                "description": "Add a new thought to your knowledge base",
                "syntax": [
                    "add <content>",
                    "add: <content>  (natural syntax)"
                ],
                "examples": [
                    "add: Had a great meeting with the design team",
                    "add Meeting notes from today's standup",
                    "add: Book recommendation - 'Atomic Habits'"
                ],
                "tips": [
                    "Use colon syntax for natural feel",
                    "Thoughts are automatically timestamped",
                    "Works offline - will sync when online"
                ]
            },
            "search": {
                "description": "Search your thoughts using semantic similarity",
                "syntax": [
                    "search <query>",
                    "search: <query>  (natural syntax)"
                ],
                "examples": [
                    "search: coffee meetings",
                    "search machine learning projects",
                    "search: ideas from last week"
                ],
                "tips": [
                    "Uses AI to find semantically similar content",
                    "Don't worry about exact keywords",
                    "Works with cached thoughts when offline"
                ]
            },
            "list": {
                "description": "List your recent thoughts",
                "syntax": [
                    "list [limit]"
                ],
                "examples": [
                    "list",
                    "list 10",
                    "list 50"
                ],
                "tips": [
                    "Default limit is 10 thoughts",
                    "Shows most recent thoughts first",
                    "Use 'show <id>' for full details"
                ]
            },
            "show": {
                "description": "Show detailed information about a specific thought",
                "syntax": [
                    "show <thought-id>"
                ],
                "examples": [
                    "show abc123",
                    "show def456789"
                ],
                "tips": [
                    "Get thought IDs from 'list' command",
                    "Shows full content and metadata",
                    "Includes related thoughts if available"
                ]
            },
            "delete": {
                "description": "Delete a thought by ID",
                "syntax": [
                    "delete <thought-id>"
                ],
                "examples": [
                    "delete abc123",
                    "rm def456  (alias)"
                ],
                "tips": [
                    "Requires confirmation",
                    "Cannot be undone",
                    "Works offline - will sync deletion"
                ]
            },
            "sync": {
                "description": "Synchronize with the server",
                "syntax": [
                    "sync"
                ],
                "examples": [
                    "sync"
                ],
                "tips": [
                    "Uploads offline changes",
                    "Downloads latest thoughts",
                    "Resolves conflicts automatically"
                ]
            },
            "stats": {
                "description": "Show statistics about your thoughts",
                "syntax": [
                    "stats"
                ],
                "examples": [
                    "stats"
                ],
                "tips": [
                    "Shows total thought count",
                    "Displays cache status",
                    "Includes sync information"
                ]
            }
        }
        
        if command in command_help:
            help_info = command_help[command]
            
            self.console.print(Panel(
                f"[bold blue]{command.upper()} Command Help[/bold blue]",
                title=f"Help: {command}",
                border_style="blue"
            ))
            
            self.console.print(f"[bold]Description:[/bold] {help_info['description']}")
            
            self.console.print(f"\n[bold]Syntax:[/bold]")
            for syntax in help_info['syntax']:
                self.console.print(f"  [cyan]{syntax}[/cyan]")
            
            self.console.print(f"\n[bold]Examples:[/bold]")
            for example in help_info['examples']:
                self.console.print(f"  [green]{example}[/green]")
            
            self.console.print(f"\n[bold]Tips:[/bold]")
            for tip in help_info['tips']:
                self.console.print(f"  • {tip}")
        else:
            self.console.print(f"[red]No detailed help available for '{command}'[/red]")
            self.console.print("Available commands: add, search, list, show, delete, sync, stats")
            self.console.print("Type 'help' for general help")
    
    async def _handle_history(self, args: List[str]) -> None:
        """Handle history command."""
        if not self.history:
            self.console.print("[yellow]No command history[/yellow]")
            return
        
        # Show last 10 commands by default
        limit = 10
        if args and args[0].isdigit():
            limit = int(args[0])
        
        recent_history = self.history[-limit:]
        
        table = Table(title="Command History")
        table.add_column("#", style="dim")
        table.add_column("Command", style="white")
        
        for i, cmd in enumerate(recent_history, 1):
            table.add_row(str(i), cmd)
        
        self.console.print(table)
    
    async def _handle_clear(self, args: List[str]) -> None:
        """Handle clear command."""
        # Clear screen
        self.console.clear()
        self._show_welcome()
    
    async def _handle_tutorial(self, args: List[str]) -> None:
        """Handle tutorial command."""
        self.console.print(Panel(
            "[bold blue]🎓 Interactive Mode Tutorial[/bold blue]\n\n"
            "Welcome to Einstein's interactive mode! This is a quick tutorial to get you started.",
            title="Tutorial",
            border_style="blue"
        ))
        
        tutorial_steps = [
            {
                "title": "Adding Thoughts",
                "content": "Use natural syntax to add thoughts:",
                "examples": [
                    "add: Had a great meeting today",
                    "add: Book recommendation - 'Deep Work'",
                    "add Meeting notes from standup"
                ]
            },
            {
                "title": "Searching",
                "content": "Search uses AI to find relevant thoughts:",
                "examples": [
                    "search: coffee meetings",
                    "search: project ideas",
                    "search machine learning"
                ]
            },
            {
                "title": "Managing Thoughts",
                "content": "List, view, and manage your thoughts:",
                "examples": [
                    "list 10",
                    "show abc123",
                    "delete def456"
                ]
            },
            {
                "title": "Getting Help",
                "content": "Get help anytime:",
                "examples": [
                    "help",
                    "help add",
                    "tips"
                ]
            }
        ]
        
        for i, step in enumerate(tutorial_steps, 1):
            self.console.print(f"\n[bold cyan]Step {i}: {step['title']}[/bold cyan]")
            self.console.print(step['content'])
            for example in step['examples']:
                self.console.print(f"  [green]{example}[/green]")
        
        self.console.print(f"\n[bold green]🎉 You're ready to go![/bold green]")
        self.console.print("Try adding your first thought or searching for something.")
        self.console.print("Type 'help' anytime for more information.")
    
    async def _handle_tips(self, args: List[str]) -> None:
        """Handle tips command."""
        tips_table = Table(title="💡 Interactive Mode Tips")
        tips_table.add_column("Tip", style="cyan", no_wrap=True)
        tips_table.add_column("Description", style="white")
        tips_table.add_column("Example", style="dim")
        
        tips_info = [
            ("Colon Syntax", "Use natural language with colons", "add: your thought"),
            ("Command Shortcuts", "Use aliases for faster typing", "h (help), q (quit), ls (list)"),
            ("Partial IDs", "You can use partial thought IDs", "show abc (instead of abc123def)"),
            ("Command History", "Access your command history", "history 20"),
            ("Context Help", "Get help on specific commands", "help search"),
            ("Offline Mode", "Works offline, syncs when online", "add: works without internet"),
            ("Clear Screen", "Clear the screen anytime", "clear"),
            ("Smart Search", "Search understands context and meaning", "search: yesterday's insights"),
            ("Batch Operations", "List multiple thoughts at once", "list 50"),
            ("Quick Exit", "Multiple ways to exit", "exit, quit, or Ctrl+D"),
        ]
        
        for tip, description, example in tips_info:
            tips_table.add_row(tip, description, example)
        
        self.console.print(tips_table)
        
        # Show contextual tips based on current state
        self.console.print("\n[bold]Contextual Tips:[/bold]")
        
        if not self.auth_manager.is_authenticated():
            self.console.print("🔐 [yellow]Not logged in?[/yellow] Exit and run: [cyan]einstein auth login[/cyan]")
        
        if hasattr(self.cached_api, 'is_offline') and self.cached_api.is_offline:
            self.console.print("📴 [yellow]Offline mode active.[/yellow] Your changes will sync when online.")
        
        self.console.print("💡 [dim]Pro tip: Use 'tutorial' for a guided walkthrough![/dim]")
    
    async def _handle_exit(self, args: List[str]) -> None:
        """Handle exit command."""
        self.running = False


@click.command()
@click.pass_context
def interactive(ctx: click.Context) -> None:
    """Start interactive mode for conversational thought management.
    
    Interactive mode provides a REPL-style interface where you can:
    - Add thoughts with natural syntax: "add: your thought here"
    - Search your knowledge base: "search: coffee meetings"
    - Manage thoughts with simple commands
    - Get help and command completion
    
    Type 'help' in interactive mode to see all available commands.
    """
    # Get components from context
    config = ctx.obj["config"]
    cached_api = ctx.obj["cached_api"]
    output = ctx.obj["output"]
    auth_manager = ctx.obj["auth_manager"]
    console = ctx.obj["console"]
    
    # Create and start interactive session
    session = InteractiveSession(config, cached_api, output, auth_manager, console)
    session.start()