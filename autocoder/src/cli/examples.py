"""
Example Commands and Usage Patterns
Helps users understand how to use AutoCoder effectively
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from .profiles import ExperienceLevel


def show_examples(console: Console, level: ExperienceLevel):
    """Show example commands based on experience level"""

    if level == ExperienceLevel.BEGINNER:
        _show_beginner_examples(console)
    elif level == ExperienceLevel.INTERMEDIATE:
        _show_intermediate_examples(console)
    else:
        _show_professional_examples(console)


def _show_beginner_examples(console: Console):
    """Show beginner-friendly examples"""

    console.print()
    intro_panel = Panel(
        """
# Example Commands for Beginners

Here are common things you can ask AutoCoder to do.
Just type naturally - no special syntax required!
""",
        title="[bold blue]Examples[/bold blue]",
        border_style="blue"
    )
    console.print(intro_panel)
    console.print()

    # Create examples table
    examples = Table(title="💡 What You Can Ask", show_header=True, header_style="bold cyan")
    examples.add_column("Category", style="yellow", no_wrap=True, width=20)
    examples.add_column("Example", style="white", width=50)
    examples.add_column("What Happens", style="dim", width=30)

    # Simple tasks
    examples.add_row(
        "Simple Functions",
        "Write a Python function to sort a list",
        "Local GPU (FREE)"
    )
    examples.add_row(
        "",
        "Create a function to calculate fibonacci",
        "Local GPU (FREE)"
    )

    # Code explanation
    examples.add_row(
        "Explanations",
        "Explain how this code works: [paste code]",
        "Local GPU (FREE)"
    )
    examples.add_row(
        "",
        "What does asyncio.gather do?",
        "Local GPU (FREE)"
    )

    # Bug fixes
    examples.add_row(
        "Bug Fixes",
        "Fix this error: [paste error message]",
        "Local or Cloud"
    )
    examples.add_row(
        "",
        "Why is my function returning None?",
        "Local GPU (FREE)"
    )

    # Larger projects
    examples.add_row(
        "Projects",
        "Build a REST API for a blog",
        "Auto-decomposed!"
    )
    examples.add_row(
        "",
        "Create a todo app with authentication",
        "Multiple subtasks"
    )

    console.print(examples)
    console.print()

    # Show model override examples
    override_panel = Panel(
        """
**Force a Specific Model:**

`@local` - Use local GPU (FREE but slower)
```
You: @local Explain how decorators work
```

`@claude` - Use Claude (fast but costs money)
```
You: @claude Design a microservices architecture
```

`@haiku` - Use Claude Haiku (fast and cheap)
```
You: @haiku Write unit tests for this function
```

**When to use each:**
• @local: Simple tasks, learning, practicing
• @claude: Complex architecture, important code, tight deadlines
• @haiku: Moderate tasks, good balance of speed and cost
""",
        title="[bold green]Model Selection[/bold green]",
        border_style="green"
    )
    console.print(override_panel)
    console.print()

    # Show commands
    commands_panel = Panel(
        """
**Useful Commands:**

• `:help` - Show all commands
• `:examples` - This screen
• `:cost` - See how much you've spent
• `:models` - List available models
• `:status` - Check GPU temperature and system status
• `:context` - View conversation history
• `:quit` - Exit AutoCoder

**Try it now!** Type `:cost` to see your current spending.
""",
        title="[bold magenta]Commands[/bold magenta]",
        border_style="magenta"
    )
    console.print(commands_panel)
    console.print()


def _show_intermediate_examples(console: Console):
    """Show intermediate examples"""

    console.print()

    # Create examples with more advanced patterns
    examples = Table(title="Example Usage Patterns", show_header=True)
    examples.add_column("Pattern", style="cyan", width=25)
    examples.add_column("Example", style="white", width=45)
    examples.add_column("Notes", style="dim", width=30)

    examples.add_row(
        "Task Decomposition",
        "Build a REST API with auth and CRUD endpoints",
        "Auto-splits into subtasks"
    )
    examples.add_row(
        "Context Building",
        "1. Create User model\n2. Add auth to that model",
        "Second task uses context"
    )
    examples.add_row(
        "Model Override",
        "@local for simple, @claude for complex",
        "Manual control when needed"
    )
    examples.add_row(
        "Budget Control",
        ":cost limit 20.00",
        "Set daily spending limit"
    )
    examples.add_row(
        "Multi-step Workflow",
        "1. Design API\n2. Implement\n3. Test\n4. Document",
        "Each step builds on previous"
    )

    console.print(examples)
    console.print()

    # Shortcuts
    shortcuts_table = Table(title="Keyboard Shortcuts", show_header=True)
    shortcuts_table.add_column("Shortcut", style="yellow", width=20)
    shortcuts_table.add_column("Action", style="white", width=40)

    shortcuts_table.add_row("Ctrl+R", "Search command history")
    shortcuts_table.add_row("↑/↓", "Navigate history")
    shortcuts_table.add_row("Ctrl+C", "Cancel current operation")
    shortcuts_table.add_row("Ctrl+D", "Exit (same as :quit)")
    shortcuts_table.add_row("Tab", "Autocomplete (for commands)")

    console.print(shortcuts_table)
    console.print()

    # Cost optimization tips
    tips_panel = Panel(
        """
**Cost Optimization Tips:**

1. Let decomposition work - complex tasks split automatically
2. Use @local for anything that doesn't require deep reasoning
3. Check :cost regularly to track spending
4. Set reasonable daily budgets with :cost limit
5. Local models are getting better - try them first!

**Typical daily cost:** $0.50 - $2.00 (vs $20+ cloud-only)
""",
        title="[bold green]Pro Tips[/bold green]",
        border_style="green"
    )
    console.print(tips_panel)
    console.print()


def _show_professional_examples(console: Console):
    """Show professional/power user examples"""

    console.print()

    # Quick reference
    quick_ref = Table(title="Quick Reference", show_header=True)
    quick_ref.add_column("Feature", style="cyan", width=25)
    quick_ref.add_column("Usage", style="white", width=50)

    quick_ref.add_row("Commands", ":h :m :c :s :ctx :q")
    quick_ref.add_row("Model Override", "@local @claude @haiku")
    quick_ref.add_row("Decomposition", "Automatic for complex tasks")
    quick_ref.add_row("Context", "Persists in ~/.autocoder/contexts/")
    quick_ref.add_row("Profile", "~/.autocoder/profile.json")
    quick_ref.add_row("Logs", "./logs/autocoder_YYYY-MM-DD.jsonl")
    quick_ref.add_row("Budget Override", ":cost limit <amount>")
    quick_ref.add_row("Disable Decomp", "Use @model override")

    console.print(quick_ref)
    console.print()

    # Advanced patterns
    patterns_panel = Panel(
        """
**Advanced Patterns:**

Multi-agent workflow:
```
Design API → Implement → Test → Deploy
(Sonnet)    (Local)     (Local)  (Haiku)
```

Context manipulation:
```
:context                  # View state
<build on previous work>  # Automatic context
```

Cost control:
```
export AUTOCODER_MAX_DAILY=50.00  # Environment var
:cost limit 100.00                # CLI override
```

Debugging:
```
cat ~/.autocoder/contexts/<session_id>.json
tail -f logs/autocoder_$(date +%Y-%m-%d).jsonl
```

Disable features:
```python
# In main.py
enable_decomposition=False
```
""",
        title="[bold yellow]Advanced Usage[/bold yellow]",
        border_style="yellow"
    )
    console.print(patterns_panel)
    console.print()


def show_quick_tips(console: Console, level: ExperienceLevel, count: int = 1):
    """Show quick inline tips"""

    from .profiles import get_tips_for_level
    import random

    tips = get_tips_for_level(level)
    if tips:
        selected = random.sample(tips, min(count, len(tips)))
        for tip in selected:
            console.print(f"[dim]{tip}[/dim]")
        console.print()
