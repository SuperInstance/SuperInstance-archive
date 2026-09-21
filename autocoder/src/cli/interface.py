"""
CLI Interface for AutoCoder
Beautiful terminal UI with streaming responses
"""

import asyncio
from typing import Optional, List
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style as PromptStyle
import os


class CLI:
    """AutoCoder CLI Interface"""

    def __init__(self, router, cost_tracker, state_manager, context_manager, profile_manager):
        self.console = Console()
        self.router = router
        self.cost_tracker = cost_tracker
        self.state_manager = state_manager
        self.context_manager = context_manager
        self.profile_manager = profile_manager

        # Load user profile
        self.profile = profile_manager.load_profile()

        # Hint counter (show hints periodically for beginners)
        self.interaction_count = 0

        # Create session context
        import uuid
        self.session_id = uuid.uuid4().hex[:8]
        self.context = context_manager.create_context(self.session_id)

        # Create history file
        history_path = os.path.expanduser("~/.autocoder_history")
        self.session = PromptSession(
            history=FileHistory(history_path),
            auto_suggest=AutoSuggestFromHistory(),
            style=PromptStyle.from_dict({
                'prompt': 'ansicyan bold',
            })
        )

    def print_banner(self):
        """Display startup banner based on user profile"""
        from .profiles import get_welcome_message

        welcome = get_welcome_message(self.profile.experience_level)
        self.console.print(welcome, style="bold blue")

        # Show quick tip for beginners
        if self.profile.show_hints and self.profile.experience_level.value == "beginner":
            from .examples import show_quick_tips
            show_quick_tips(self.console, self.profile.experience_level, count=1)

    def parse_model_override(self, text: str) -> Optional[str]:
        """
        Parse model override syntax: @model_name

        Examples:
            @claude → force Claude
            @local → force local model
            @haiku → force Claude Haiku
        """
        if text.startswith("@claude"):
            return "claude"
        elif text.startswith("@local"):
            return "local"
        elif text.startswith("@haiku"):
            return "haiku"
        return None

    def strip_model_prefix(self, text: str) -> str:
        """Remove @model prefix from text"""
        if text.startswith("@"):
            parts = text.split(maxsplit=1)
            return parts[1] if len(parts) > 1 else ""
        return text

    async def handle_command(self, cmd: str):
        """Handle : commands"""
        cmd = cmd.lower()

        if cmd == ":quit" or cmd == ":exit" or cmd == ":q":
            raise EOFError

        elif cmd == ":help" or cmd == ":h":
            self.show_help()

        elif cmd == ":models" or cmd == ":m":
            self.show_models()

        elif cmd == ":cost" or cmd == ":c":
            self.show_costs()

        elif cmd == ":status" or cmd == ":s":
            self.show_status()

        elif cmd == ":context" or cmd == ":ctx":
            self.show_context()

        elif cmd == ":examples" or cmd == ":ex":
            self.show_examples()

        elif cmd == ":profile":
            self.show_profile()

        elif cmd.startswith(":profile set"):
            await self.set_profile(cmd)

        elif cmd == ":setup":
            await self.run_setup()

        elif cmd.startswith(":cost limit"):
            try:
                limit = float(cmd.split()[-1])
                self.cost_tracker.set_daily_limit(limit)
                self.console.print(f"✓ Daily budget limit set to ${limit:.2f}", style="green")
            except (ValueError, IndexError):
                self.console.print("Usage: :cost limit <amount>", style="red")

        elif cmd == ":clear":
            self.console.clear()
            self.print_banner()

        else:
            self.console.print(f"Unknown command: {cmd}", style="red")
            self.console.print("Type ':help' for available commands", style="dim")

    def show_help(self):
        """Display help information"""
        help_table = Table(title="AutoCoder Commands", show_header=True)
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")

        # Commands
        help_table.add_row(":help, :h", "Show this help message")
        help_table.add_row(":examples, :ex", "Show usage examples")
        help_table.add_row(":models, :m", "List available models")
        help_table.add_row(":cost, :c", "Show cost breakdown")
        help_table.add_row(":status, :s", "Show system status")
        help_table.add_row(":context, :ctx", "Show conversation context")
        help_table.add_row(":profile", "Show your profile settings")
        help_table.add_row(":profile set <level>", "Change experience level")
        help_table.add_row(":setup", "Run setup wizard")
        help_table.add_row(":cost limit <amount>", "Set daily budget limit")
        help_table.add_row(":clear", "Clear screen")
        help_table.add_row(":quit, :q", "Exit AutoCoder")

        self.console.print()
        self.console.print(help_table)
        self.console.print()

        # Model selection
        model_table = Table(title="Model Selection", show_header=True)
        model_table.add_column("Syntax", style="cyan", no_wrap=True)
        model_table.add_column("Description", style="white")

        model_table.add_row("@claude <prompt>", "Force use Claude 4 Sonnet")
        model_table.add_row("@local <prompt>", "Force use local model (Qwen)")
        model_table.add_row("@haiku <prompt>", "Force use Claude Haiku (fast)")
        model_table.add_row("<prompt>", "Auto-route to best model")

        self.console.print(model_table)
        self.console.print()

    def show_models(self):
        """Display available models"""
        models_table = Table(title="Available Models", show_header=True)
        models_table.add_column("Model", style="cyan")
        models_table.add_column("Type", style="yellow")
        models_table.add_column("Cost", style="green")
        models_table.add_column("Status", style="white")

        # Get models from router
        models = self.router.get_available_models()

        for model_info in models:
            models_table.add_row(
                model_info['name'],
                model_info['type'],
                model_info['cost'],
                model_info['status']
            )

        self.console.print()
        self.console.print(models_table)
        self.console.print()

    def show_costs(self):
        """Display cost breakdown"""
        costs = self.cost_tracker.get_breakdown()

        cost_table = Table(title="Cost Breakdown", show_header=True)
        cost_table.add_column("Item", style="cyan")
        cost_table.add_column("Amount", style="green", justify="right")

        cost_table.add_row("Session Total", f"${costs['total']:.4f}")
        cost_table.add_row("Today's Total", f"${costs['today']:.2f}")
        cost_table.add_row("Remaining Budget", f"${costs['remaining']:.2f}")

        if costs.get('by_model'):
            cost_table.add_row("", "")  # Separator
            for model, cost in costs['by_model'].items():
                cost_table.add_row(f"  {model}", f"${cost:.4f}")

        self.console.print()
        self.console.print(cost_table)

        # Cache savings
        if costs.get('cache_savings', 0) > 0:
            self.console.print(
                f"\n💾 Cache savings: ${costs['cache_savings']:.2f}",
                style="green"
            )

        self.console.print()

    def show_status(self):
        """Display system status"""
        status = self.state_manager.get_system_status()

        status_table = Table(title="System Status", show_header=True)
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="white")

        # GPU status
        if status.get('gpu'):
            gpu = status['gpu']
            status_table.add_row(
                "GPU",
                f"{gpu['name']} ({gpu['vram_used']}/{gpu['vram_total']} MB, {gpu['temp']}°C)"
            )

        # Loaded models
        if status.get('loaded_models'):
            status_table.add_row(
                "Loaded Models",
                ", ".join(status['loaded_models'])
            )

        # Task count
        status_table.add_row("Tasks Completed", str(status.get('tasks_completed', 0)))

        # Uptime
        if status.get('uptime'):
            status_table.add_row("Session Uptime", status['uptime'])

        self.console.print()
        self.console.print(status_table)
        self.console.print()

    def show_context(self):
        """Display current conversation context"""
        context_table = Table(title="Conversation Context", show_header=True)
        context_table.add_column("Metric", style="cyan")
        context_table.add_column("Value", style="white")

        # Message count
        context_table.add_row("Total Messages", str(len(self.context.messages)))

        # Task statistics
        completed = self.context.get_completed_tasks()
        pending = self.context.get_pending_tasks()
        failed = self.context.get_failed_tasks()

        context_table.add_row("Completed Tasks", str(len(completed)))
        context_table.add_row("Pending Tasks", str(len(pending)))
        context_table.add_row("Failed Tasks", str(len(failed)))

        # Artifacts
        context_table.add_row("Stored Artifacts", str(len(self.context.artifacts)))

        # Session info
        duration = (self.context.updated_at - self.context.created_at).total_seconds()
        minutes = int(duration // 60)
        context_table.add_row("Session Duration", f"{minutes} minutes")

        self.console.print()
        self.console.print(context_table)

        # Show recent context summary
        if len(self.context.messages) > 0:
            self.console.print()
            summary = self.context.get_conversation_summary()
            panel = Panel(
                summary,
                title="[bold cyan]Context Summary[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(panel)

        self.console.print()

    def show_examples(self):
        """Display usage examples"""
        from .examples import show_examples
        show_examples(self.console, self.profile.experience_level)

    def show_profile(self):
        """Display current profile settings"""
        profile_table = Table(title="Your Profile", show_header=True)
        profile_table.add_column("Setting", style="cyan")
        profile_table.add_column("Value", style="white")

        profile_table.add_row("Experience Level", self.profile.experience_level.value.upper())
        profile_table.add_row("Show Hints", "Yes" if self.profile.show_hints else "No")
        profile_table.add_row("Show Routing Details", "Yes" if self.profile.show_routing_details else "No")
        profile_table.add_row("Auto-Decompose", "Yes" if self.profile.auto_decompose else "No")
        profile_table.add_row("Confirm Expensive Tasks", "Yes" if self.profile.confirm_expensive_tasks else "No")
        profile_table.add_row("Daily Budget Limit", f"${self.profile.daily_budget_limit:.2f}")

        self.console.print()
        self.console.print(profile_table)
        self.console.print()
        self.console.print("[dim]Change with: :profile set <beginner|intermediate|professional>[/dim]")
        self.console.print()

    async def set_profile(self, cmd: str):
        """Set user profile"""
        from .profiles import ExperienceLevel

        parts = cmd.split()
        if len(parts) < 3:
            self.console.print("[red]Usage: :profile set <beginner|intermediate|professional>[/red]")
            return

        level_name = parts[2].lower()
        level_map = {
            "beginner": ExperienceLevel.BEGINNER,
            "intermediate": ExperienceLevel.INTERMEDIATE,
            "professional": ExperienceLevel.PROFESSIONAL,
            "pro": ExperienceLevel.PROFESSIONAL
        }

        if level_name not in level_map:
            self.console.print(f"[red]Unknown level: {level_name}[/red]")
            self.console.print("[dim]Options: beginner, intermediate, professional[/dim]")
            return

        level = level_map[level_name]
        self.profile_manager.set_profile(level)
        self.profile = self.profile_manager.profile

        self.console.print(f"✓ Profile set to [bold]{level.value.upper()}[/bold]")
        self.console.print("[dim]Restart AutoCoder to see the new welcome message[/dim]\n")

    async def run_setup(self):
        """Run setup wizard"""
        from .wizard import WelcomeWizard

        wizard = WelcomeWizard(self.console, self.profile_manager)
        await wizard.run()

        # Reload profile
        self.profile = self.profile_manager.load_profile()

    async def stream_response(self, provider, messages, model_name: str):
        """Stream response with live updates"""
        full_response = ""

        with Live(console=self.console, refresh_per_second=10) as live:
            async for chunk in provider.chat(messages, stream=True):
                full_response += chunk

                # Update display with markdown rendering
                panel = Panel(
                    Markdown(full_response),
                    title=f"[bold blue]{model_name}[/bold blue]",
                    border_style="blue"
                )
                live.update(panel)

        self.console.print()  # Add newline after response
        return full_response

    async def run(self):
        """Main CLI loop with decomposition support"""
        self.print_banner()

        # Show if decomposition is enabled
        if self.router.enable_decomposition and self.router.decomposer:
            self.console.print("[dim]✨ Task decomposition enabled (complex tasks will be broken down)[/dim]\n")

        while True:
            try:
                # Get user input
                user_input = await self.session.prompt_async("You: ")

                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith(":"):
                    await self.handle_command(user_input)
                    continue

                # Parse model override
                model_override = self.parse_model_override(user_input)
                clean_input = self.strip_model_prefix(user_input)

                # Progress callback for decomposition updates
                progress_messages = []

                def progress_callback(msg):
                    progress_messages.append(msg)
                    self.console.print(f"[dim]{msg}[/dim]")

                # Route task with decomposition support
                try:
                    response_text, metadata = await self.router.route_with_decomposition(
                        clean_input,
                        self.context,
                        override=model_override,
                        progress_callback=progress_callback
                    )

                    # Display the response
                    panel = Panel(
                        Markdown(response_text),
                        title="[bold blue]Response[/bold blue]",
                        border_style="blue"
                    )
                    self.console.print(panel)
                    self.console.print()

                    # Track cost
                    # For decomposed tasks, estimate total cost from all subtasks
                    total_cost = 0
                    total_input_tokens = 0
                    total_output_tokens = 0

                    if metadata.get('decomposed'):
                        # Estimate tokens for decomposed task
                        for task_id in metadata['results'].get('completed_tasks', []):
                            task = self.context.get_task(task_id)
                            if task and task.result:
                                # Rough estimation
                                input_est = len(task.description) // 4
                                output_est = len(task.result) // 4
                                total_input_tokens += input_est
                                total_output_tokens += output_est

                                # Get cost estimate from assigned model
                                if task.assigned_model in ['sonnet', 'haiku']:
                                    model_key = f'claude-{task.assigned_model}'
                                    if model_key in self.router.providers:
                                        provider = self.router.providers[model_key]
                                        cost = provider.estimate_cost(input_est, output_est)
                                        total_cost += cost
                    else:
                        # Single model execution
                        model_name = metadata.get('model', '')
                        total_input_tokens = len(clean_input) // 4
                        total_output_tokens = len(response_text) // 4

                        # Find provider to estimate cost
                        for provider in self.router.providers.values():
                            if provider.get_model_name() == model_name:
                                total_cost = provider.estimate_cost(total_input_tokens, total_output_tokens)
                                break

                    # Record cost
                    if total_cost > 0:
                        model_info = metadata.get('model', 'decomposed' if metadata.get('decomposed') else 'unknown')
                        self.cost_tracker.record_cost(
                            model_info,
                            total_cost,
                            total_input_tokens,
                            total_output_tokens
                        )

                        # Show cost if significant
                        if total_cost >= 0.01:
                            self.console.print(f"[dim]💰 Cost: ${total_cost:.4f}[/dim]\n")

                    # Save to state
                    self.state_manager.record_interaction(
                        user_input=clean_input,
                        response=response_text,
                        model=metadata.get('model', 'decomposed'),
                        cost=total_cost
                    )

                    # Save context periodically
                    self.context_manager.save_context(self.session_id)

                except Exception as e:
                    self.console.print(f"\n❌ Error during task execution: {str(e)}", style="red")
                    import traceback
                    traceback.print_exc()

            except KeyboardInterrupt:
                self.console.print("\n[dim]Use :quit to exit[/dim]")
                continue

            except EOFError:
                self.console.print("\n👋 Goodbye!", style="bold blue")
                # Save final context
                self.context_manager.save_context(self.session_id)
                break

            except Exception as e:
                self.console.print(f"\n❌ Error: {str(e)}", style="red")
                self.console.print("[dim]Check logs for details[/dim]")
                import traceback
                traceback.print_exc()
