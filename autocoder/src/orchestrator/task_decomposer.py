"""
Task Decomposer
Uses a complex model (Claude) to break down tasks into simpler subtasks
that can be executed by simpler models
"""

import asyncio
import json
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from .context import SharedContext, SubTask, TaskStatus, MessageRole
from .analyzer import TaskComplexity


@dataclass
class DecompositionPlan:
    """A plan for executing a complex task through decomposition"""
    original_task: str
    subtasks: List[SubTask]
    execution_strategy: str  # 'sequential', 'parallel', 'dag'
    estimated_time_seconds: Optional[int] = None
    estimated_cost: Optional[float] = None


class TaskDecomposer:
    """
    Decomposes complex tasks into simpler subtasks
    Uses Claude to analyze and break down tasks
    """

    def __init__(self, decomposer_provider, analyzer):
        """
        Initialize task decomposer

        Args:
            decomposer_provider: Model provider to use for decomposition (typically Claude)
            analyzer: TaskAnalyzer instance for complexity assessment
        """
        self.decomposer_provider = decomposer_provider
        self.analyzer = analyzer

    async def should_decompose(self, task: str, context: SharedContext) -> bool:
        """
        Determine if a task should be decomposed

        Args:
            task: Task description
            context: Current shared context

        Returns:
            True if task should be decomposed
        """
        # Analyze task complexity
        analysis = self.analyzer.analyze(task)

        # Decompose if:
        # 1. Task is complex or very complex
        # 2. Task mentions multiple steps or components
        # 3. Task has words like "design", "implement", "refactor", "build"

        if analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.VERY_COMPLEX]:
            return True

        decompose_keywords = [
            'design and implement',
            'build a',
            'create a system',
            'refactor',
            'multiple',
            'step by step',
            'first.*then',
            'architecture'
        ]

        import re
        task_lower = task.lower()
        for keyword in decompose_keywords:
            if re.search(keyword, task_lower):
                return True

        return False

    async def decompose(self, task: str, context: SharedContext) -> DecompositionPlan:
        """
        Decompose a complex task into subtasks

        Args:
            task: Complex task description
            context: Current shared context

        Returns:
            DecompositionPlan with subtasks
        """
        # Build decomposition prompt
        decomposition_prompt = self._build_decomposition_prompt(task, context)

        # Get decomposition from Claude
        messages = [
            {'role': 'user', 'content': decomposition_prompt}
        ]

        # Call Claude to decompose
        response = await self.decomposer_provider.chat(
            messages=messages,
            temperature=0.3,  # Lower temperature for more structured output
            max_tokens=2000
        )

        # Parse the decomposition
        plan = self._parse_decomposition(response, task, context)

        # Log decomposition in context
        context.add_message(
            role=MessageRole.SYSTEM,
            content=f"Decomposed task into {len(plan.subtasks)} subtasks",
            metadata={
                'original_task': task,
                'subtask_count': len(plan.subtasks),
                'strategy': plan.execution_strategy
            }
        )

        return plan

    def _build_decomposition_prompt(self, task: str, context: SharedContext) -> str:
        """Build the prompt for task decomposition"""

        context_summary = context.get_conversation_summary()

        prompt = f"""You are a task decomposition expert. Break down the following complex task into simple, atomic subtasks.

Original Task: {task}

Context:
{context_summary}

Please decompose this task into subtasks following these guidelines:

1. Each subtask should be simple enough for a 7B parameter model to complete
2. Subtasks should be atomic (one clear objective each)
3. Identify dependencies between subtasks
4. Suggest which model should handle each subtask:
   - "local" for simple tasks (formatting, simple functions, basic fixes)
   - "haiku" for moderate tasks (features, tests, moderate refactoring)
   - "sonnet" for complex tasks (architecture decisions, security, complex logic)

5. Specify execution strategy:
   - "sequential" if tasks must be done in order
   - "parallel" if tasks can be done simultaneously
   - "dag" if there's a dependency graph

Return your decomposition in this JSON format:

{{
  "strategy": "sequential|parallel|dag",
  "estimated_time_seconds": <number>,
  "estimated_cost": <number>,
  "subtasks": [
    {{
      "id": "task_1",
      "description": "Clear description of what to do",
      "suggested_model": "local|haiku|sonnet",
      "dependencies": [],
      "reasoning": "Why this subtask and why this model"
    }},
    ...
  ]
}}

IMPORTANT: Return ONLY valid JSON, no additional text."""

        return prompt

    def _parse_decomposition(self, response: str, original_task: str,
                           context: SharedContext) -> DecompositionPlan:
        """Parse the decomposition response into a plan"""

        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            # Create SubTask objects
            subtasks = []
            for task_data in data.get('subtasks', []):
                subtask = SubTask(
                    id=task_data.get('id', f"task_{uuid.uuid4().hex[:8]}"),
                    parent_id=None,  # Could link to parent task if needed
                    description=task_data['description'],
                    status=TaskStatus.PENDING,
                    assigned_model=task_data.get('suggested_model', 'local'),
                    dependencies=task_data.get('dependencies', []),
                    metadata={
                        'reasoning': task_data.get('reasoning', ''),
                        'original_task': original_task
                    }
                )
                subtasks.append(subtask)

                # Add to context
                context.add_task(subtask)

            # Create plan
            plan = DecompositionPlan(
                original_task=original_task,
                subtasks=subtasks,
                execution_strategy=data.get('strategy', 'sequential'),
                estimated_time_seconds=data.get('estimated_time_seconds'),
                estimated_cost=data.get('estimated_cost')
            )

            return plan

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: create a simple plan with the original task
            print(f"⚠️  Failed to parse decomposition: {e}")
            print(f"Response was: {response[:200]}...")

            # Create a single subtask as fallback
            fallback_task = SubTask(
                id=f"task_{uuid.uuid4().hex[:8]}",
                parent_id=None,
                description=original_task,
                status=TaskStatus.PENDING,
                assigned_model='sonnet',  # Use complex model for safety
                metadata={'fallback': True, 'original_task': original_task}
            )

            context.add_task(fallback_task)

            return DecompositionPlan(
                original_task=original_task,
                subtasks=[fallback_task],
                execution_strategy='sequential'
            )

    async def execute_plan(self, plan: DecompositionPlan, context: SharedContext,
                          model_providers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a decomposition plan

        Args:
            plan: DecompositionPlan to execute
            context: SharedContext for tracking progress
            model_providers: Dict of available model providers

        Returns:
            Dict with results
        """
        results = {
            'success': True,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_time': 0,
            'total_cost': 0.0
        }

        if plan.execution_strategy == 'sequential':
            results = await self._execute_sequential(plan, context, model_providers)
        elif plan.execution_strategy == 'parallel':
            results = await self._execute_parallel(plan, context, model_providers)
        elif plan.execution_strategy == 'dag':
            results = await self._execute_dag(plan, context, model_providers)

        return results

    async def _execute_sequential(self, plan: DecompositionPlan, context: SharedContext,
                                 model_providers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute subtasks sequentially"""
        from datetime import datetime

        results = {
            'success': True,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_time': 0,
            'total_cost': 0.0
        }

        for subtask in plan.subtasks:
            start_time = datetime.now()

            # Update task status
            context.update_task_status(subtask.id, TaskStatus.IN_PROGRESS)

            try:
                # Get the appropriate provider
                provider = self._get_provider_for_model(subtask.assigned_model, model_providers)

                if not provider:
                    raise Exception(f"No provider available for model: {subtask.assigned_model}")

                # Build context for this subtask
                messages = context.get_context_for_model()
                messages.append({
                    'role': 'user',
                    'content': f"Subtask: {subtask.description}\n\nComplete this subtask based on the context above."
                })

                # Execute subtask
                response = await provider.chat(messages=messages, temperature=0.7)

                # Record success
                duration = (datetime.now() - start_time).total_seconds()
                context.update_task_status(subtask.id, TaskStatus.COMPLETED, result=response)
                context.add_message(
                    role=MessageRole.ASSISTANT,
                    content=response,
                    model=subtask.assigned_model,
                    metadata={'subtask_id': subtask.id, 'duration': duration}
                )

                results['completed_tasks'].append(subtask.id)
                results['total_time'] += duration

            except Exception as e:
                # Record failure
                context.update_task_status(subtask.id, TaskStatus.FAILED, error=str(e))
                results['failed_tasks'].append(subtask.id)
                results['success'] = False

                # Stop on first failure in sequential mode
                break

        return results

    async def _execute_parallel(self, plan: DecompositionPlan, context: SharedContext,
                               model_providers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute independent subtasks in parallel"""

        tasks = []
        for subtask in plan.subtasks:
            task_coroutine = self._execute_single_task(subtask, context, model_providers)
            tasks.append(task_coroutine)

        # Execute all in parallel
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        results = {
            'success': True,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_time': 0,
            'total_cost': 0.0
        }

        for i, result in enumerate(results_list):
            if isinstance(result, Exception):
                results['failed_tasks'].append(plan.subtasks[i].id)
                results['success'] = False
            else:
                results['completed_tasks'].append(result['task_id'])
                results['total_time'] = max(results['total_time'], result['duration'])

        return results

    async def _execute_dag(self, plan: DecompositionPlan, context: SharedContext,
                          model_providers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute subtasks respecting dependency graph"""

        results = {
            'success': True,
            'completed_tasks': [],
            'failed_tasks': [],
            'total_time': 0,
            'total_cost': 0.0
        }

        while True:
            # Get tasks ready to execute (dependencies met)
            ready_tasks = context.get_pending_tasks()

            if not ready_tasks:
                break  # All done or blocked

            # Execute ready tasks in parallel
            task_coroutines = [
                self._execute_single_task(task, context, model_providers)
                for task in ready_tasks
            ]

            results_list = await asyncio.gather(*task_coroutines, return_exceptions=True)

            # Update results
            for i, result in enumerate(results_list):
                if isinstance(result, Exception):
                    results['failed_tasks'].append(ready_tasks[i].id)
                    results['success'] = False
                else:
                    results['completed_tasks'].append(result['task_id'])

        return results

    async def _execute_single_task(self, subtask: SubTask, context: SharedContext,
                                  model_providers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single subtask"""
        from datetime import datetime

        start_time = datetime.now()
        context.update_task_status(subtask.id, TaskStatus.IN_PROGRESS)

        try:
            provider = self._get_provider_for_model(subtask.assigned_model, model_providers)

            if not provider:
                raise Exception(f"No provider for model: {subtask.assigned_model}")

            # Build messages with context
            messages = context.get_context_for_model()
            messages.append({
                'role': 'user',
                'content': f"Subtask: {subtask.description}\n\nComplete this subtask."
            })

            response = await provider.chat(messages=messages, temperature=0.7)
            duration = (datetime.now() - start_time).total_seconds()

            context.update_task_status(subtask.id, TaskStatus.COMPLETED, result=response)
            context.add_message(
                role=MessageRole.ASSISTANT,
                content=response,
                model=subtask.assigned_model,
                metadata={'subtask_id': subtask.id, 'duration': duration}
            )

            return {'task_id': subtask.id, 'duration': duration, 'success': True}

        except Exception as e:
            context.update_task_status(subtask.id, TaskStatus.FAILED, error=str(e))
            raise

    def _get_provider_for_model(self, model_name: str, providers: Dict[str, Any]):
        """Map model name to provider"""
        model_map = {
            'local': 'local',
            'haiku': 'claude-haiku',
            'sonnet': 'claude-sonnet'
        }

        provider_key = model_map.get(model_name, model_name)
        return providers.get(provider_key)
