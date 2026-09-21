#!/usr/bin/env python3
"""
AutoCoder - Multi-Model Coding Assistant
Main entry point
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.cli.interface import CLI
from src.cli.profiles import ProfileManager
from src.cli.wizard import run_welcome_wizard_if_needed
from src.orchestrator.router import Router
from src.orchestrator.cost_tracker import CostTracker
from src.orchestrator.context import ContextManager
from src.state.manager import StateManager
from src.hardware.thermal import ThermalManager, PowerManager
from src.config.loader import ConfigLoader
from src.providers.ollama import OllamaProvider
from src.providers.claude import ClaudeProvider


async def main():
    """Main application entry point"""

    print("🚀 Starting AutoCoder...")

    # Initialize profile manager (do this first)
    profile_manager = ProfileManager()
    print("✓ Profile manager initialized")

    # Run welcome wizard if first time
    from rich.console import Console
    console = Console()

    if profile_manager.is_first_run():
        print("\n🎉 Welcome! Running first-time setup...\n")
        await run_welcome_wizard_if_needed(console, profile_manager)
        print()

    # Load configuration
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'proart_px13.yaml')
        config = ConfigLoader.load(config_path)
        env_vars = ConfigLoader.load_env()
        print("✓ Configuration loaded")
    except FileNotFoundError:
        print("❌ Configuration file not found")
        print("   Expected: config/proart_px13.yaml")
        return 1
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        return 1

    # Initialize components
    try:
        # Cost tracker
        cost_tracker = CostTracker(
            daily_limit=config.daily_budget,
            monthly_limit=config.monthly_budget
        )
        print("✓ Cost tracker initialized")

        # State manager
        state_manager = StateManager(
            save_conversations=config.save_conversations,
            log_dir="./logs"
        )
        print("✓ State manager initialized")

        # Context manager (for task decomposition and agent handoff)
        context_manager = ContextManager(persist_dir="./contexts")
        print("✓ Context manager initialized")

        # Thermal & power management (laptop)
        thermal_manager = None
        power_manager = None

        if config.thermal_enabled and config.hardware.is_laptop:
            thermal_manager = ThermalManager(
                max_temp=config.hardware.gpu_max_temp,
                max_continuous_minutes=30,
                cooldown_seconds=60
            )
            power_manager = PowerManager()
            print("✓ Thermal/power management enabled")

        # Initialize model providers
        providers = {}

        # Local model (Ollama)
        try:
            ollama_config = config.models.get('ollama_primary')
            if ollama_config:
                providers['local'] = OllamaProvider(
                    model_name=ollama_config.name,
                    base_url=os.getenv('OLLAMA_HOST', 'http://localhost:11434')
                )
                print(f"✓ Local model configured: {ollama_config.name}")
        except Exception as e:
            print(f"⚠️  Local model not available: {e}")
            print("   (Run: sudo bash install_ollama.sh)")

        # Claude models
        anthropic_key = env_vars.get('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY')

        if anthropic_key:
            # Claude Sonnet
            sonnet_config = config.models.get('claude_primary')
            if sonnet_config:
                try:
                    providers['claude-sonnet'] = ClaudeProvider(
                        model_name=sonnet_config.name,
                        api_key=anthropic_key
                    )
                    print(f"✓ Claude Sonnet configured: {sonnet_config.name}")
                except Exception as e:
                    print(f"⚠️  Claude Sonnet error: {e}")

            # Claude Haiku
            haiku_config = config.models.get('claude_fast')
            if haiku_config:
                try:
                    providers['claude-haiku'] = ClaudeProvider(
                        model_name=haiku_config.name,
                        api_key=anthropic_key
                    )
                    print(f"✓ Claude Haiku configured: {haiku_config.name}")
                except Exception as e:
                    print(f"⚠️  Claude Haiku error: {e}")
        else:
            print("⚠️  ANTHROPIC_API_KEY not set (cloud models unavailable)")
            print("   Set with: export ANTHROPIC_API_KEY='your-key'")

        # Check if we have at least one provider
        if not providers:
            print("\n❌ No model providers available!")
            print("   Need either:")
            print("   1. Ollama installed (run: sudo bash install_ollama.sh)")
            print("   2. ANTHROPIC_API_KEY set")
            return 1

        print(f"\n✓ {len(providers)} model(s) ready")

        # Initialize router with decomposition support
        router = Router(
            providers=providers,
            budget_manager=cost_tracker,
            thermal_manager=thermal_manager,
            power_manager=power_manager,
            enable_decomposition=True  # Enable task decomposition
        )
        print("✓ Router initialized")

        # Show decomposition status
        if router.decomposer:
            print("✓ Task decomposition enabled (complex tasks will be broken down)")
        else:
            print("⚠️  Task decomposition unavailable (need Claude Sonnet for decomposition)")

        # Initialize CLI
        cli = CLI(
            router=router,
            cost_tracker=cost_tracker,
            state_manager=state_manager,
            context_manager=context_manager,
            profile_manager=profile_manager
        )
        print("✓ CLI initialized\n")

        # Run CLI
        await cli.run()

        # Show session summary on exit
        print("\n" + "="*60)
        print("Session Summary")
        print("="*60)
        print(cost_tracker.get_cost_summary())
        print("\nStatistics:")
        stats = state_manager.get_statistics()
        print(f"  Total interactions: {stats['total_interactions']}")
        print(f"  Models used: {', '.join(stats['models_used'].keys())}")

        # Show routing stats
        router_stats = router.get_stats()
        print(f"\nRouting Statistics:")
        print(f"  Total routes: {router_stats['total_routes']}")
        print(f"  Auto-routed: {router_stats['auto_routes']}")
        print(f"  Manual overrides: {router_stats['overrides']}")
        if router_stats.get('decomposed_tasks', 0) > 0:
            print(f"  Decomposed tasks: {router_stats['decomposed_tasks']}")
            print(f"  Subtasks executed: {router_stats['subtasks_executed']}")

        # Offer to export session
        try:
            response = input("\nExport session? (y/n): ")
            if response.lower() == 'y':
                filename = f"session_{state_manager.session_start.strftime('%Y%m%d_%H%M%S')}.json"
                state_manager.export_session(filename)
                print(f"✓ Session exported to: {filename}")
        except:
            pass

        return 0

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 0
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
