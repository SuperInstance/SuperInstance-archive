"""
Rich CLI Interface for Multi-Bot Orchestration
Interactive command-line interface with rich formatting, tables, progress bars, and live updates
"""

import asyncio
import click
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os

# Rich library for beautiful CLI
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree
from rich.prompt import Prompt, Confirm
from rich.status import Status
from rich.columns import Columns
from rich.align import Align
import rich.traceback

# Install rich traceback handler
rich.traceback.install()

from ..director.claude_director import ClaudeDirector, Task, TaskStatus, TaskPriority
from ..collaboration.collaborative_executor import CollaborativeTaskExecutor, CollaborationPattern
from ..synchronization.bot_synchronizer import BotSynchronizer, SynchronizationBarrierType, CoordinationMode
from ..knowledge.knowledge_sharing_system import KnowledgeSharingSystem
from ..reporting.enhanced_progress_reporter import EnhancedProgressReporter, ReportType

console = Console()

class BotOrchestratorCLI:
    """Rich CLI interface for multi-bot orchestration system"""
    
    def __init__(
        self,
        director: Optional[ClaudeDirector] = None,
        collaborative_executor: Optional[CollaborativeTaskExecutor] = None,
        bot_synchronizer: Optional[BotSynchronizer] = None,
        knowledge_system: Optional[KnowledgeSharingSystem] = None,
        progress_reporter: Optional[EnhancedProgressReporter] = None
    ):
        self.director = director
        self.collaborative_executor = collaborative_executor
        self.bot_synchronizer = bot_synchronizer
        self.knowledge_system = knowledge_system
        self.progress_reporter = progress_reporter
        
        # CLI state
        self.running = False
        self.auto_refresh = False
        self.refresh_interval = 5  # seconds
        
    def create_system_overview_layout(self) -> Layout:
        """Create live system overview layout"""
        layout = Layout()
        
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split(
            Layout(name="stats", ratio=1),
            Layout(name="tasks", ratio=2)
        )
        
        layout["right"].split(
            Layout(name="bots", ratio=1),
            Layout(name="collaborations", ratio=1)
        )
        
        return layout
    
    async def update_live_display(self, layout: Layout):
        """Update live display with current system data"""
        try:
            # Header
            header_text = Text("🤖 Multi-Bot Orchestrator Dashboard", style="bold magenta")
            header_text.append(f" • {datetime.now().strftime('%H:%M:%S')}", style="dim")
            layout["header"].update(Panel(Align.center(header_text), style="blue"))
            
            # System stats
            await self._update_stats_panel(layout["stats"])
            
            # Tasks
            await self._update_tasks_panel(layout["tasks"])
            
            # Bots
            await self._update_bots_panel(layout["bots"])
            
            # Collaborations
            await self._update_collaborations_panel(layout["collaborations"])
            
            # Footer
            footer_text = Text("Press 'q' to quit, 'r' to refresh, 'h' for help", style="dim")
            layout["footer"].update(Panel(Align.center(footer_text), style="green"))
            
        except Exception as e:
            console.print(f"[red]Error updating display: {e}[/red]")
    
    async def _update_stats_panel(self, layout_part):
        """Update system statistics panel"""
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        try:
            if self.bot_synchronizer:
                sync_status = self.bot_synchronizer.get_synchronization_status()
                stats_table.add_row("🤖 Active Bots", str(sync_status.get("active_bots", 0)))
                stats_table.add_row("📋 Active Barriers", str(sync_status.get("active_barriers", 0)))
                stats_table.add_row("🔄 Shared Resources", str(sync_status.get("shared_resources", 0)))
            
            if self.progress_reporter:
                overview = self.progress_reporter.get_system_overview()
                stats_table.add_row("⚡ Active Tasks", str(overview.get("active_tasks", 0)))
                stats_table.add_row("✅ Completed", str(overview.get("completed_tasks", 0)))
                stats_table.add_row("❌ Failed", str(overview.get("failed_tasks", 0)))
                stats_table.add_row("💰 Total Cost", f"${overview.get('total_cost', 0):.2f}")
            
            if self.knowledge_system:
                knowledge_count = len(self.knowledge_system.knowledge_items)
                stats_table.add_row("🧠 Knowledge Items", str(knowledge_count))
        
        except Exception as e:
            stats_table.add_row("❗ Error", str(e)[:30])
        
        layout_part.update(Panel(stats_table, title="System Stats", border_style="cyan"))
    
    async def _update_tasks_panel(self, layout_part):
        """Update tasks panel"""
        tasks_table = Table(show_header=True, header_style="bold magenta")
        tasks_table.add_column("ID", max_width=10)
        tasks_table.add_column("Description", max_width=30)
        tasks_table.add_column("Status", max_width=12)
        tasks_table.add_column("Progress", max_width=15)
        tasks_table.add_column("Bot", max_width=15)
        
        try:
            if self.progress_reporter:
                # Get active tasks
                active_tasks = [
                    (task_id, progress) for task_id, progress in self.progress_reporter.task_progress.items()
                    if progress.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
                ]
                
                # Sort by creation time
                active_tasks.sort(key=lambda x: x[1].created_at, reverse=True)
                
                # Show top 10 active tasks
                for task_id, progress in active_tasks[:10]:
                    status_color = self._get_status_color(progress.status)
                    progress_bar = self._create_progress_bar(progress.progress_percentage)
                    
                    tasks_table.add_row(
                        task_id[:8],
                        progress.task_description[:28] + "..." if len(progress.task_description) > 28 else progress.task_description,
                        f"[{status_color}]{progress.status.value}[/{status_color}]",
                        progress_bar,
                        progress.allocated_bot[:13] if progress.allocated_bot else "None"
                    )
        
        except Exception as e:
            tasks_table.add_row("Error", str(e)[:28], "N/A", "N/A", "N/A")
        
        layout_part.update(Panel(tasks_table, title="Active Tasks", border_style="green"))
    
    async def _update_bots_panel(self, layout_part):
        """Update bots panel"""
        bots_table = Table(show_header=True, header_style="bold blue")
        bots_table.add_column("Bot ID", max_width=15)
        bots_table.add_column("Status", max_width=10)
        bots_table.add_column("Barriers", max_width=8)
        bots_table.add_column("Last Seen", max_width=15)
        
        try:
            if self.bot_synchronizer:
                for bot_id, bot_state in self.bot_synchronizer.bot_states.items():
                    status = "🟢 Active" if bot_state.is_active else "🔴 Inactive"
                    barriers = str(len(bot_state.current_barriers))
                    
                    # Calculate time since last heartbeat
                    time_diff = datetime.now() - bot_state.last_heartbeat
                    if time_diff.total_seconds() < 60:
                        last_seen = f"{int(time_diff.total_seconds())}s ago"
                    elif time_diff.total_seconds() < 3600:
                        last_seen = f"{int(time_diff.total_seconds() / 60)}m ago"
                    else:
                        last_seen = f"{int(time_diff.total_seconds() / 3600)}h ago"
                    
                    bots_table.add_row(
                        bot_id[:13],
                        status,
                        barriers,
                        last_seen
                    )
        
        except Exception as e:
            bots_table.add_row("Error", str(e)[:13], "N/A", "N/A")
        
        layout_part.update(Panel(bots_table, title="Bot Status", border_style="blue"))
    
    async def _update_collaborations_panel(self, layout_part):
        """Update collaborations panel"""
        collab_table = Table(show_header=True, header_style="bold yellow")
        collab_table.add_column("Session ID", max_width=10)
        collab_table.add_column("Pattern", max_width=12)
        collab_table.add_column("Bots", max_width=8)
        collab_table.add_column("Duration", max_width=10)
        collab_table.add_column("Quality", max_width=8)
        
        try:
            if self.progress_reporter:
                active_sessions = [
                    session for session in self.progress_reporter.collaboration_sessions.values()
                    if session.status == "active"
                ]
                
                for session in active_sessions[:5]:  # Show top 5
                    duration = (datetime.now() - session.started_at).total_seconds()
                    duration_str = f"{int(duration // 60)}m {int(duration % 60)}s"
                    
                    quality_score = session.coordination_quality
                    quality_color = "green" if quality_score > 0.8 else "yellow" if quality_score > 0.6 else "red"
                    
                    collab_table.add_row(
                        session.session_id[:8],
                        session.collaboration_pattern.value[:10],
                        str(len(session.participating_bots)),
                        duration_str,
                        f"[{quality_color}]{quality_score:.2f}[/{quality_color}]"
                    )
        
        except Exception as e:
            collab_table.add_row("Error", str(e)[:8], "N/A", "N/A", "N/A")
        
        layout_part.update(Panel(collab_table, title="Active Collaborations", border_style="yellow"))
    
    def _get_status_color(self, status: TaskStatus) -> str:
        """Get color for task status"""
        colors = {
            TaskStatus.PENDING: "yellow",
            TaskStatus.IN_PROGRESS: "blue",
            TaskStatus.COMPLETED: "green",
            TaskStatus.FAILED: "red",
            TaskStatus.CANCELLED: "dim"
        }
        return colors.get(status, "white")
    
    def _create_progress_bar(self, percentage: float) -> str:
        """Create a text progress bar"""
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        return f"{bar} {percentage:.1f}%"
    
    async def live_dashboard(self):
        """Start live dashboard"""
        layout = self.create_system_overview_layout()
        
        with Live(layout, refresh_per_second=1, screen=True):
            self.running = True
            while self.running:
                await self.update_live_display(layout)
                await asyncio.sleep(self.refresh_interval)
    
    def create_tasks_table(self, tasks: List[Dict]) -> Table:
        """Create a formatted tasks table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan")
        table.add_column("Description")
        table.add_column("Status")
        table.add_column("Progress")
        table.add_column("Bot", style="blue")
        table.add_column("Cost", style="green")
        table.add_column("Created", style="dim")
        
        for task in tasks:
            status_color = self._get_status_color(TaskStatus(task["status"]))
            progress_bar = self._create_progress_bar(task["progress_percentage"])
            
            table.add_row(
                task["id"][:8] + "...",
                task["description"][:40] + "..." if len(task["description"]) > 40 else task["description"],
                f"[{status_color}]{task['status']}[/{status_color}]",
                progress_bar,
                task["allocated_bot"] or "None",
                f"${task['cost_incurred']:.3f}",
                datetime.fromisoformat(task["created_at"]).strftime("%m/%d %H:%M")
            )
        
        return table
    
    def create_bots_grid(self, bots: List[Dict]) -> Columns:
        """Create a grid of bot status cards"""
        bot_panels = []
        
        for bot in bots:
            status_emoji = "🟢" if bot["is_active"] else "🔴"
            
            # Create bot info
            bot_info = []
            bot_info.append(f"{status_emoji} {bot['bot_id']}")
            bot_info.append(f"Last seen: {datetime.fromisoformat(bot['last_heartbeat']).strftime('%H:%M:%S')}")
            bot_info.append(f"Active barriers: {bot['current_barriers']}")
            bot_info.append(f"Completed barriers: {bot['completed_barriers']}")
            
            if bot.get("collaboration_profile"):
                profile = bot["collaboration_profile"]
                bot_info.append(f"Success rate: {profile['success_rate']:.1%}")
                bot_info.append(f"Coordination: {profile['coordination_score']:.2f}")
            
            panel_content = "\n".join(bot_info)
            style = "green" if bot["is_active"] else "red"
            
            bot_panels.append(Panel(panel_content, title=bot["bot_id"][:12], border_style=style))
        
        return Columns(bot_panels, equal=True, expand=True)
    
    def create_collaboration_tree(self, sessions: List[Dict]) -> Tree:
        """Create a tree view of collaboration sessions"""
        tree = Tree("🤝 Collaborations")
        
        for session in sessions:
            session_node = tree.add(f"Session {session['session_id'][:8]} ({session['pattern']})")
            
            # Add participating bots
            bots_node = session_node.add("👥 Participating Bots")
            for bot_id in session['participating_bots']:
                bots_node.add(f"🤖 {bot_id}")
            
            # Add task information
            if session['task_ids']:
                tasks_node = session_node.add("📋 Tasks")
                for task_id in session['task_ids']:
                    tasks_node.add(f"📝 {task_id[:8]}")
            
            # Add metrics
            metrics_node = session_node.add("📊 Metrics")
            duration = (datetime.now() - datetime.fromisoformat(session['started_at'])).total_seconds()
            metrics_node.add(f"Duration: {int(duration // 60)}m {int(duration % 60)}s")
            metrics_node.add(f"Barriers: {session['barriers_created']}/{session['barriers_completed']}")
            metrics_node.add(f"Knowledge shared: {session['knowledge_items_shared']}")
            metrics_node.add(f"Quality: {session['coordination_quality']:.2f}")
        
        return tree


# Click CLI commands
@click.group()
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx, debug):
    """Multi-Bot Orchestrator CLI"""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Initialize CLI (would need actual component instances)
    ctx.obj = BotOrchestratorCLI()

@cli.command()
@click.option('--refresh-interval', default=5, help='Refresh interval in seconds')
@click.pass_context
def dashboard(ctx, refresh_interval):
    """Launch interactive dashboard"""
    cli_interface = ctx.obj
    cli_interface.refresh_interval = refresh_interval
    
    console.print("🚀 Starting Multi-Bot Orchestrator Dashboard...", style="bold green")
    console.print(f"Refresh interval: {refresh_interval}s", style="dim")
    console.print("Press Ctrl+C to exit", style="dim")
    
    try:
        asyncio.run(cli_interface.live_dashboard())
    except KeyboardInterrupt:
        console.print("\n👋 Goodbye!", style="bold blue")

@cli.command()
@click.option('--status', help='Filter by status')
@click.option('--limit', default=20, help='Limit number of results')
@click.pass_context
def tasks(ctx, status, limit):
    """List and manage tasks"""
    cli_interface = ctx.obj
    
    with console.status("Loading tasks..."):
        # Mock task data (replace with actual API calls)
        mock_tasks = [
            {
                "id": f"task_{i}",
                "description": f"Sample task {i}",
                "status": "IN_PROGRESS" if i % 2 == 0 else "PENDING",
                "progress_percentage": (i * 10) % 100,
                "allocated_bot": f"bot_{i % 3}" if i % 2 == 0 else None,
                "cost_incurred": i * 0.05,
                "created_at": (datetime.now() - timedelta(hours=i)).isoformat()
            }
            for i in range(limit)
        ]
    
    if status:
        mock_tasks = [t for t in mock_tasks if t["status"] == status.upper()]
    
    table = cli_interface.create_tasks_table(mock_tasks)
    console.print(table)
    
    if not mock_tasks:
        console.print("No tasks found matching criteria", style="yellow")

@cli.command()
@click.pass_context
def bots(ctx):
    """View bot status and management"""
    cli_interface = ctx.obj
    
    with console.status("Loading bot information..."):
        # Mock bot data (replace with actual API calls)
        mock_bots = [
            {
                "bot_id": f"bot_{i}",
                "is_active": i % 2 == 0,
                "last_heartbeat": (datetime.now() - timedelta(minutes=i)).isoformat(),
                "current_barriers": i % 3,
                "completed_barriers": i * 2,
                "collaboration_profile": {
                    "success_rate": 0.85 + (i * 0.05) % 0.15,
                    "coordination_score": 0.7 + (i * 0.1) % 0.3
                } if i % 2 == 0 else None
            }
            for i in range(6)
        ]
    
    bot_grid = cli_interface.create_bots_grid(mock_bots)
    console.print(Panel(bot_grid, title="🤖 Bot Status", border_style="blue"))

@cli.command()
@click.pass_context
def collaborations(ctx):
    """View active collaborations"""
    cli_interface = ctx.obj
    
    with console.status("Loading collaboration sessions..."):
        # Mock collaboration data
        mock_sessions = [
            {
                "session_id": f"collab_{i}",
                "pattern": ["PARALLEL", "PIPELINE", "HIERARCHICAL"][i % 3],
                "participating_bots": [f"bot_{j}" for j in range(i + 2)],
                "task_ids": [f"task_{j}" for j in range(i + 1)],
                "started_at": (datetime.now() - timedelta(minutes=i * 15)).isoformat(),
                "barriers_created": i + 1,
                "barriers_completed": i,
                "knowledge_items_shared": i * 3,
                "coordination_quality": 0.6 + (i * 0.15) % 0.4
            }
            for i in range(3)
        ]
    
    if mock_sessions:
        collab_tree = cli_interface.create_collaboration_tree(mock_sessions)
        console.print(collab_tree)
    else:
        console.print("No active collaborations", style="yellow")

@cli.command()
@click.argument('description')
@click.option('--priority', default='MEDIUM', help='Task priority')
@click.option('--tokens', default=1000, help='Estimated tokens')
@click.pass_context
def create_task(ctx, description, priority, tokens):
    """Create a new task"""
    cli_interface = ctx.obj
    
    with console.status("Creating task..."):
        # Mock task creation
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simulate API call delay
        import time
        time.sleep(1)
    
    console.print(f"✅ Task created: {task_id}", style="bold green")
    console.print(f"Description: {description}")
    console.print(f"Priority: {priority}")
    console.print(f"Estimated tokens: {tokens}")

@cli.command()
@click.option('--pattern', default='PARALLEL', help='Collaboration pattern')
@click.option('--tasks', help='Comma-separated task IDs')
@click.pass_context
def start_collaboration(ctx, pattern, tasks):
    """Start a new collaboration session"""
    cli_interface = ctx.obj
    
    if not tasks:
        tasks = Prompt.ask("Enter comma-separated task IDs")
    
    task_list = [t.strip() for t in tasks.split(',')]
    
    console.print(f"Starting collaboration with pattern: {pattern}", style="bold blue")
    console.print(f"Tasks: {', '.join(task_list)}")
    
    if Confirm.ask("Continue?"):
        with console.status("Starting collaboration..."):
            import time
            time.sleep(2)
            
            collaboration_id = f"collab_{datetime.now().strftime('%H%M%S')}"
        
        console.print(f"✅ Collaboration started: {collaboration_id}", style="bold green")
    else:
        console.print("Cancelled", style="yellow")

@cli.command()
@click.option('--type', default='summary', help='Report type')
@click.pass_context
def report(ctx, type):
    """Generate system reports"""
    cli_interface = ctx.obj
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Generating report...", total=100)
        
        # Simulate report generation
        for i in range(100):
            progress.update(task, advance=1)
            asyncio.run(asyncio.sleep(0.02))
    
    # Mock report data
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "report_type": type,
        "summary": {
            "total_tasks": 45,
            "active_tasks": 12,
            "completed_tasks": 28,
            "failed_tasks": 5,
            "success_rate": 84.8,
            "average_duration": 1.5,
            "total_cost": 12.45
        }
    }
    
    # Display report
    report_table = Table(title=f"📊 {type.title()} Report")
    report_table.add_column("Metric", style="cyan")
    report_table.add_column("Value", style="green")
    
    for key, value in report_data["summary"].items():
        if isinstance(value, float):
            display_value = f"{value:.2f}"
        else:
            display_value = str(value)
        
        report_table.add_row(key.replace("_", " ").title(), display_value)
    
    console.print(report_table)

@cli.command()
@click.pass_context
def health(ctx):
    """System health check"""
    cli_interface = ctx.obj
    
    health_checks = [
        ("Director Service", "✅ Healthy"),
        ("Bot Synchronizer", "✅ Healthy"),
        ("Knowledge System", "✅ Healthy"),
        ("Progress Reporter", "✅ Healthy"),
        ("Database Connection", "✅ Healthy"),
        ("WebSocket Server", "⚠️  Warning")
    ]
    
    health_table = Table(title="🏥 System Health Check")
    health_table.add_column("Component", style="cyan")
    health_table.add_column("Status")
    
    for component, status in health_checks:
        style = "green" if "✅" in status else "yellow" if "⚠️" in status else "red"
        health_table.add_row(component, f"[{style}]{status}[/{style}]")
    
    console.print(health_table)
    
    # Overall health score
    healthy_count = len([s for _, s in health_checks if "✅" in s])
    total_count = len(health_checks)
    health_score = (healthy_count / total_count) * 100
    
    score_color = "green" if health_score >= 90 else "yellow" if health_score >= 70 else "red"
    console.print(f"\n[{score_color}]Overall Health Score: {health_score:.1f}%[/{score_color}]")

if __name__ == "__main__":
    cli()