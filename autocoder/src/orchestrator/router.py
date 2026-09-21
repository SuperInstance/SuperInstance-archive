"""
Smart Router
Routes tasks to optimal models based on complexity and constraints
Supports task decomposition for complex tasks
"""

import asyncio
from typing import Optional, Dict, Any, Tuple, Callable
from .analyzer import TaskAnalyzer, TaskAnalysis
from .context import SharedContext
from .task_decomposer import TaskDecomposer, DecompositionPlan
from ..providers.base import ModelProvider


class Router:
    """
    Routes tasks to appropriate models
    Supports manual override, intelligent routing, and task decomposition
    """

    def __init__(
        self,
        providers: Dict[str, ModelProvider],
        budget_manager=None,
        thermal_manager=None,
        power_manager=None,
        enable_decomposition: bool = True
    ):
        """
        Initialize router

        Args:
            providers: Dict of model providers {'local': OllamaProvider, 'sonnet': ClaudeProvider, ...}
            budget_manager: Optional budget tracking
            thermal_manager: Optional thermal monitoring (for laptop)
            power_manager: Optional power status detection
            enable_decomposition: Whether to enable task decomposition (default: True)
        """
        self.providers = providers
        self.analyzer = TaskAnalyzer()
        self.budget_manager = budget_manager
        self.thermal_manager = thermal_manager
        self.power_manager = power_manager
        self.enable_decomposition = enable_decomposition

        # Initialize task decomposer if we have a suitable provider (Claude Sonnet)
        self.decomposer = None
        if enable_decomposition and 'claude-sonnet' in providers:
            self.decomposer = TaskDecomposer(
                decomposer_provider=providers['claude-sonnet'],
                analyzer=self.analyzer
            )

        # Routing statistics
        self.stats = {
            'total_routes': 0,
            'by_model': {},
            'overrides': 0,
            'auto_routes': 0,
            'decomposed_tasks': 0,
            'subtasks_executed': 0
        }

    async def route(
        self,
        task: str,
        override: Optional[str] = None
    ) -> Tuple[ModelProvider, Optional[TaskAnalysis]]:
        """
        Route task to appropriate model

        Args:
            task: User's task description
            override: Optional manual model selection ('local', 'sonnet', 'haiku')

        Returns:
            (provider, analysis) tuple
        """
        self.stats['total_routes'] += 1

        # Manual override takes precedence
        if override:
            self.stats['overrides'] += 1
            provider = self._resolve_provider(override)
            return provider, None

        # Analyze task
        analysis = self.analyzer.analyze(task)
        self.stats['auto_routes'] += 1

        # Check constraints
        suggested_model = await self._apply_constraints(analysis)

        # Get provider
        provider = self._resolve_provider(suggested_model)

        # Update stats
        model_name = provider.get_model_name()
        self.stats['by_model'][model_name] = self.stats['by_model'].get(model_name, 0) + 1

        return provider, analysis

    async def route_with_decomposition(
        self,
        task: str,
        context: SharedContext,
        override: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Route task with optional decomposition for complex tasks

        Args:
            task: User's task description
            context: SharedContext for tracking progress
            override: Optional manual model selection
            progress_callback: Optional callback(message) for progress updates

        Returns:
            (final_response, metadata) tuple
        """
        self.stats['total_routes'] += 1

        # Check if decomposition should be used
        should_decompose = False

        if self.decomposer and not override and self.enable_decomposition:
            should_decompose = await self.decomposer.should_decompose(task, context)

        if should_decompose:
            return await self._route_with_decomposition(task, context, progress_callback)
        else:
            # Standard routing
            return await self._route_standard(task, context, override, progress_callback)

    async def _route_with_decomposition(
        self,
        task: str,
        context: SharedContext,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Execute task using decomposition"""

        if progress_callback:
            progress_callback("🔄 Analyzing task complexity and planning decomposition...")

        # Decompose the task
        plan = await self.decomposer.decompose(task, context)

        self.stats['decomposed_tasks'] += 1
        self.stats['subtasks_executed'] += len(plan.subtasks)

        if progress_callback:
            progress_callback(f"📋 Task decomposed into {len(plan.subtasks)} subtasks")
            progress_callback(f"   Strategy: {plan.execution_strategy}")
            for i, subtask in enumerate(plan.subtasks, 1):
                progress_callback(f"   {i}. [{subtask.assigned_model}] {subtask.description}")

        # Execute the plan
        if progress_callback:
            progress_callback(f"\n⚡ Executing {len(plan.subtasks)} subtasks...")

        results = await self.decomposer.execute_plan(plan, context, self.providers)

        # Build final response from completed tasks
        completed_results = []
        for task_id in results['completed_tasks']:
            task = context.get_task(task_id)
            if task and task.result:
                completed_results.append(f"**{task.description}**\n{task.result}\n")

        final_response = "\n---\n\n".join(completed_results) if completed_results else "Task completed"

        # Add summary
        summary = f"\n\n---\n\n**Decomposition Summary:**\n"
        summary += f"- Total subtasks: {len(plan.subtasks)}\n"
        summary += f"- Completed: {len(results['completed_tasks'])}\n"
        summary += f"- Failed: {len(results['failed_tasks'])}\n"
        summary += f"- Strategy: {plan.execution_strategy}\n"

        final_response += summary

        metadata = {
            'decomposed': True,
            'subtask_count': len(plan.subtasks),
            'strategy': plan.execution_strategy,
            'results': results
        }

        return final_response, metadata

    async def _route_standard(
        self,
        task: str,
        context: SharedContext,
        override: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Standard routing without decomposition"""

        # Route to single model
        provider, analysis = await self.route(task, override)

        model_name = provider.get_model_name()

        if progress_callback:
            if override:
                progress_callback(f"→ Using {model_name} (manual override)")
            else:
                complexity = analysis.complexity.name if analysis else "UNKNOWN"
                progress_callback(f"→ Routing to {model_name} (complexity: {complexity})")

        # Build messages from context
        messages = context.get_context_for_model()
        messages.append({'role': 'user', 'content': task})

        # Execute
        response = await provider.chat(messages=messages, temperature=0.7)

        # Update context
        from .context import MessageRole
        context.add_message(MessageRole.USER, task)
        context.add_message(MessageRole.ASSISTANT, response, model=model_name)

        metadata = {
            'decomposed': False,
            'model': model_name,
            'complexity': analysis.complexity.value if analysis else None
        }

        return response, metadata

    async def _apply_constraints(self, analysis: TaskAnalysis) -> str:
        """
        Apply runtime constraints (budget, thermal, power) to routing decision

        Args:
            analysis: Task analysis

        Returns:
            Model identifier after applying constraints
        """
        suggested = analysis.suggested_model

        # Check budget constraints
        if self.budget_manager and self.budget_manager.is_near_limit():
            # Force local-only if budget critical
            if suggested in ['sonnet', 'haiku']:
                suggested = 'local'

        # Check thermal constraints (laptop)
        if self.thermal_manager and self.thermal_manager.should_throttle():
            # Avoid local GPU if overheating
            if suggested == 'local':
                suggested = 'haiku'  # Use fast cloud instead

        # Check power status (laptop)
        if self.power_manager and self.power_manager.is_on_battery():
            # On battery: prefer cloud for moderate+ tasks
            if analysis.complexity.value >= 3 and suggested == 'local':
                suggested = 'haiku'

        return suggested

    def _resolve_provider(self, model_id: str) -> ModelProvider:
        """
        Resolve model identifier to provider

        Args:
            model_id: Model identifier ('local', 'sonnet', 'haiku', 'claude')

        Returns:
            ModelProvider instance
        """
        # Map identifiers to provider keys
        mapping = {
            'local': 'local',
            'ollama': 'local',
            'qwen': 'local',
            'sonnet': 'claude-sonnet',
            'claude': 'claude-sonnet',
            'haiku': 'claude-haiku',
            'gpt4': 'openai-gpt4',
            'gpt': 'openai-gpt4'
        }

        provider_key = mapping.get(model_id, model_id)

        if provider_key not in self.providers:
            # Fallback to local if provider not found
            print(f"Warning: Provider '{provider_key}' not found, using local")
            provider_key = 'local'

        return self.providers[provider_key]

    def get_available_models(self) -> list[Dict[str, str]]:
        """
        Get list of available models for display

        Returns:
            List of model info dicts
        """
        models = []

        for key, provider in self.providers.items():
            model_name = provider.get_model_name()

            # Determine cost string
            if hasattr(provider, 'estimate_cost'):
                cost_sample = provider.estimate_cost(1000, 1000)
                if cost_sample > 0:
                    cost_str = f"${cost_sample:.4f}/1K"
                else:
                    cost_str = "FREE"
            else:
                cost_str = "FREE"

            # Determine type
            if 'local' in key or 'ollama' in key:
                model_type = "Local (GPU)"
            else:
                model_type = "Cloud (API)"

            # Check status
            status = "✓ Ready"
            if 'local' in key:
                # Could check if Ollama is running
                status = "✓ Ready" if self._check_local_available() else "⚠ Not loaded"

            models.append({
                'name': model_name,
                'type': model_type,
                'cost': cost_str,
                'status': status
            })

        return models

    def _check_local_available(self) -> bool:
        """Check if local model is available"""
        # Simple check - could be expanded
        try:
            provider = self.providers.get('local')
            return provider is not None
        except:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            **self.stats,
            'auto_route_percentage': (
                self.stats['auto_routes'] / self.stats['total_routes'] * 100
                if self.stats['total_routes'] > 0 else 0
            ),
            'override_percentage': (
                self.stats['overrides'] / self.stats['total_routes'] * 100
                if self.stats['total_routes'] > 0 else 0
            )
        }
