"""
Welcome Wizard
Interactive setup for first-time users
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from .profiles import ExperienceLevel, ProfileManager


class WelcomeWizard:
    """Interactive welcome wizard for new users"""

    def __init__(self, console: Console, profile_manager: ProfileManager):
        self.console = console
        self.profile_manager = profile_manager

    async def run(self) -> bool:
        """
        Run the welcome wizard

        Returns:
            True if setup completed, False if skipped
        """
        # Welcome message
        self.console.clear()
        welcome_panel = Panel(
            """
# Welcome to AutoCoder! 🎉

AutoCoder is a smart coding assistant that helps you write code faster while saving money.

**How it works:**
• Simple tasks run on your GPU for FREE
• Complex tasks use cloud AI (Claude) only when needed
• Tasks are automatically broken down to minimize costs

**What you'll save:**
• 83-97% compared to using Claude alone
• Most tasks cost $0 (run locally on your GPU)
• Complex tasks cost ~$0.15-0.50 instead of $2-5

Let's get you set up in 2 minutes!
""",
            title="[bold blue]Welcome[/bold blue]",
            border_style="blue"
        )
        self.console.print(welcome_panel)
        self.console.print()

        # Ask if they want guided setup
        wants_setup = Confirm.ask(
            "Would you like help setting up AutoCoder?",
            default=True
        )

        if not wants_setup:
            self.console.print("[dim]You can run ':setup' anytime to configure settings.[/dim]\n")
            # Use default beginner profile
            self.profile_manager.set_profile(ExperienceLevel.BEGINNER)
            return False

        # Step 1: Experience level
        level = self._ask_experience_level()

        # Step 2: Budget preferences (if not beginner)
        if level != ExperienceLevel.BEGINNER:
            self._ask_budget_preferences()

        # Step 3: Check prerequisites
        self._check_prerequisites()

        # Step 4: Quick tutorial
        if level == ExperienceLevel.BEGINNER:
            self._show_quick_tutorial()

        # Save profile
        self.profile_manager.set_profile(level)
        self.profile_manager.mark_tutorial_completed()

        # Success message
        success_panel = Panel(
            f"""
# Setup Complete! ✅

Your profile: **{level.value.upper()}**

You're ready to start coding! Try these commands:

• Just ask a question: "Write a Python function to sort a list"
• Get help: `:help`
• See examples: `:examples`
• Check costs: `:cost`

**Tip:** Start with simple tasks to get comfortable!
""",
            title="[bold green]Ready to Go![/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)
        self.console.print()

        return True

    def _ask_experience_level(self) -> ExperienceLevel:
        """Ask user for their experience level"""

        self.console.print()
        level_panel = Panel(
            """
# Choose Your Experience Level

This helps AutoCoder tailor the interface to your needs:

**1. Beginner** - New to AI coding assistants
   • Helpful hints and tips
   • Detailed explanations
   • Warnings before expensive operations
   • Perfect for learning!

**2. Intermediate** - Some experience with AI tools
   • Fewer hints
   • Keyboard shortcuts enabled
   • Higher daily budget
   • Good balance of help and efficiency

**3. Professional** - I know what I'm doing
   • Minimal UI, maximum efficiency
   • No confirmations or warnings
   • Highest daily budget
   • Shortcuts and power features

You can always change this later with `:profile`
""",
            title="[bold cyan]Experience Level[/bold cyan]",
            border_style="cyan"
        )
        self.console.print(level_panel)
        self.console.print()

        choice = Prompt.ask(
            "Choose your level",
            choices=["1", "2", "3", "beginner", "intermediate", "professional"],
            default="1"
        )

        # Map choice to level
        level_map = {
            "1": ExperienceLevel.BEGINNER,
            "beginner": ExperienceLevel.BEGINNER,
            "2": ExperienceLevel.INTERMEDIATE,
            "intermediate": ExperienceLevel.INTERMEDIATE,
            "3": ExperienceLevel.PROFESSIONAL,
            "professional": ExperienceLevel.PROFESSIONAL
        }

        level = level_map[choice.lower()]
        self.console.print(f"\n✓ Set to [bold]{level.value.upper()}[/bold] mode\n")

        return level

    def _ask_budget_preferences(self):
        """Ask about budget preferences"""

        self.console.print()
        budget_panel = Panel(
            """
# Daily Budget

AutoCoder tracks your spending and warns you when approaching limits.

**Typical usage:**
• Beginner: $5/day (plenty for learning)
• Intermediate: $10/day (active development)
• Professional: $50/day (heavy usage)

**Remember:** 70-80% of tasks run locally for FREE!
""",
            title="[bold yellow]Budget Settings[/bold yellow]",
            border_style="yellow"
        )
        self.console.print(budget_panel)
        self.console.print()

        wants_custom = Confirm.ask(
            "Do you want to set a custom daily budget?",
            default=False
        )

        if wants_custom:
            while True:
                try:
                    budget = float(Prompt.ask("Daily budget in USD", default="10.0"))
                    if budget > 0:
                        self.profile_manager.profile.daily_budget_limit = budget
                        self.console.print(f"✓ Daily budget set to ${budget:.2f}\n")
                        break
                    else:
                        self.console.print("[red]Budget must be positive[/red]")
                except ValueError:
                    self.console.print("[red]Please enter a valid number[/red]")

    def _check_prerequisites(self):
        """Check and explain prerequisites"""

        self.console.print()
        prereq_panel = Panel(
            """
# Setup Check

AutoCoder needs either (or both):

**Option 1: Local Model (FREE)** 🆓
• Runs on your GPU
• Perfect for most tasks
• No API key needed
• Status: [yellow]Checking...[/yellow]

**Option 2: Cloud Models (Paid)** 💳
• Fast cloud inference
• Best for complex tasks
• Requires API key from Anthropic
• Status: [yellow]Checking...[/yellow]

Checking your setup...
""",
            title="[bold magenta]Prerequisites[/bold magenta]",
            border_style="magenta"
        )
        self.console.print(prereq_panel)
        self.console.print()

        import subprocess
        import os

        # Check Ollama
        ollama_available = False
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0 and "qwen2.5-coder" in result.stdout.decode():
                self.console.print("✅ Local model (Ollama) is ready!")
                ollama_available = True
            else:
                self.console.print("⚠️  Local model not found")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.console.print("⚠️  Ollama not installed")

        # Check API key
        api_key_available = bool(os.getenv('ANTHROPIC_API_KEY'))
        if api_key_available:
            self.console.print("✅ Claude API key is configured!")
        else:
            self.console.print("⚠️  No Claude API key found")

        self.console.print()

        # Provide guidance
        if not ollama_available and not api_key_available:
            help_panel = Panel(
                """
# Action Required

You need at least one option to proceed:

**To use local models (FREE):**
```bash
sudo bash install_ollama.sh
bash setup_complete.sh
```

**To use cloud models:**
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

**Get an API key:**
1. Visit https://console.anthropic.com
2. Sign up (free trial available!)
3. Copy your API key

Run the commands above, then restart AutoCoder.
""",
                title="[bold red]Setup Needed[/bold red]",
                border_style="red"
            )
            self.console.print(help_panel)

        elif not ollama_available:
            self.console.print("[dim]💡 Tip: Install Ollama for FREE local inference[/dim]")
            self.console.print("[dim]   Run: sudo bash install_ollama.sh[/dim]\n")

        elif not api_key_available:
            self.console.print("[dim]💡 Tip: Add API key for faster, more powerful models[/dim]")
            self.console.print("[dim]   Run: export ANTHROPIC_API_KEY='...'[/dim]\n")

    def _show_quick_tutorial(self):
        """Show quick tutorial for beginners"""

        self.console.print()
        tutorial_panel = Panel(
            """
# Quick Tutorial (1 minute)

**How to use AutoCoder:**

1. **Just type your request:**
   ```
   You: Write a Python function to calculate fibonacci numbers
   ```
   AutoCoder will choose the best model automatically!

2. **Check costs anytime:**
   ```
   You: :cost
   ```

3. **Force a specific model:**
   ```
   You: @local Write a simple hello world
   You: @claude Design a complex system architecture
   ```

4. **Get help:**
   ```
   You: :help
   ```

5. **See examples:**
   ```
   You: :examples
   ```

**Tips for beginners:**
• Start with simple tasks to get comfortable
• Green text means FREE (ran locally)
• Check `:cost` to see your spending
• Use `:help` whenever you're stuck

Ready to try it out!
""",
            title="[bold green]Quick Start[/bold green]",
            border_style="green"
        )
        self.console.print(tutorial_panel)
        self.console.print()


async def run_welcome_wizard_if_needed(console: Console, profile_manager: ProfileManager) -> bool:
    """
    Run welcome wizard if this is first run

    Args:
        console: Rich console
        profile_manager: Profile manager instance

    Returns:
        True if wizard was run, False otherwise
    """
    if profile_manager.is_first_run():
        wizard = WelcomeWizard(console, profile_manager)
        await wizard.run()
        return True
    return False
