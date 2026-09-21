# src/resources/resource_manager.py
"""
Resource Manager - CPU/GPU allocation and API rate limiting
Optimized for RTX 4050 GPU + multi-core CPU
"""

import asyncio
import time
import os
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import multiprocessing
from aiolimiter import AsyncLimiter


@dataclass
class APIProviderConfig:
    """Configuration for an API provider"""
    name: str
    rpm_limit: int  # Requests per minute
    cost_per_1k_input: float  # Cost per 1K input tokens
    cost_per_1k_output: float  # Cost per 1K output tokens
    daily_limit: Optional[float] = None  # Daily cost limit in dollars


class ResourceManager:
    """
    Manages system resources:
    - CPU core pool for parallel execution
    - GPU queue for sequential image generation
    - API rate limiting per provider
    - Cost tracking across all providers
    """

    def __init__(self, cpu_cores: Optional[int] = None, gpu_available: bool = True):
        """
        Initialize resource manager

        Args:
            cpu_cores: Number of CPU cores to use (default: auto-detect)
            gpu_available: Whether GPU is available (RTX 4050)
        """
        # CPU Pool
        if cpu_cores is None:
            cpu_cores = max(1, multiprocessing.cpu_count() - 1)  # Leave one core free

        self.cpu_cores = cpu_cores
        self.cpu_semaphore = asyncio.Semaphore(cpu_cores)
        self.cpu_active = 0

        print(f"💻 CPU Pool: {cpu_cores} cores available")

        # GPU Queue (RTX 4050)
        self.gpu_available = gpu_available
        self.gpu_queue = asyncio.Queue() if gpu_available else None
        self.gpu_active = False
        self.gpu_current_task = None

        if gpu_available:
            asyncio.create_task(self._gpu_worker())
            print(f"🎮 GPU Queue: RTX 4050 ready")
        else:
            print(f"⚠️ GPU: Not available")

        # API Rate Limiters
        self.api_providers = {
            "anthropic": APIProviderConfig(
                name="Anthropic",
                rpm_limit=50,
                cost_per_1k_input=3.0,  # Claude Sonnet
                cost_per_1k_output=15.0,
                daily_limit=100.0
            ),
            "openai": APIProviderConfig(
                name="OpenAI",
                rpm_limit=500,
                cost_per_1k_input=0.15,  # GPT-4o mini
                cost_per_1k_output=0.60,
                daily_limit=50.0
            ),
            "groq": APIProviderConfig(
                name="Groq",
                rpm_limit=30,  # Free tier
                cost_per_1k_input=0.0,  # Free!
                cost_per_1k_output=0.0,
                daily_limit=None  # No cost limit for free tier
            ),
            "together": APIProviderConfig(
                name="Together AI",
                rpm_limit=60,
                cost_per_1k_input=0.20,
                cost_per_1k_output=0.20,
                daily_limit=50.0
            )
        }

        # Rate limiting: {provider: [timestamp of last N requests]}
        self.api_request_times = {
            provider: [] for provider in self.api_providers.keys()
        }

        # Cost tracking
        self.costs = {
            provider: 0.0 for provider in self.api_providers.keys()
        }
        self.cost_history = []  # List of (timestamp, provider, cost) tuples

        # Global daily cost limit
        self.global_daily_limit = 200.0  # $200/day max

        print(f"🌐 API Providers configured: {', '.join(self.api_providers.keys())}")

    async def execute_with_cpu(self, agent_id: str, task_func: Callable) -> Any:
        """
        Execute task with CPU resource allocation

        Args:
            agent_id: ID of the agent requesting resources
            task_func: Async function to execute

        Returns:
            Result from task_func
        """
        async with self.cpu_semaphore:
            self.cpu_active += 1
            try:
                result = await task_func()
                return result
            finally:
                self.cpu_active -= 1

    async def execute_with_gpu(self, agent_id: str, task_func: Callable, priority: str = "normal") -> Any:
        """
        Queue task for GPU execution

        Args:
            agent_id: ID of the agent requesting GPU
            task_func: Async function to execute on GPU
            priority: "high", "normal", or "low"

        Returns:
            Result from task_func
        """
        if not self.gpu_available:
            raise Exception("GPU not available")

        # Create future for result
        result_future = asyncio.Future()

        # Add to queue with priority
        await self.gpu_queue.put((priority, time.time(), agent_id, task_func, result_future))

        # Wait for result
        return await result_future

    async def _gpu_worker(self):
        """
        Worker that processes GPU queue one task at a time
        RTX 4050 can only handle one GPU task at a time efficiently
        """
        while True:
            # Get next task
            priority, queued_time, agent_id, task_func, result_future = await self.gpu_queue.get()

            self.gpu_active = True
            self.gpu_current_task = {
                "agent_id": agent_id,
                "started": time.time(),
                "wait_time": time.time() - queued_time
            }

            try:
                # Execute on GPU
                result = await task_func()
                result_future.set_result(result)

            except Exception as e:
                result_future.set_exception(e)

            finally:
                self.gpu_active = False
                self.gpu_current_task = None
                self.gpu_queue.task_done()

    async def call_api(
        self,
        provider: str,
        api_func: Callable,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> Any:
        """
        Execute API call with rate limiting and cost tracking

        Args:
            provider: API provider name ("anthropic", "openai", etc.)
            api_func: Async function that makes the API call
            input_tokens: Estimated input tokens (for cost tracking)
            output_tokens: Estimated output tokens (for cost tracking)

        Returns:
            Result from api_func

        Raises:
            Exception if rate limited or cost limit exceeded
        """
        if provider not in self.api_providers:
            raise ValueError(f"Unknown provider: {provider}")

        config = self.api_providers[provider]

        # Check cost limits
        await self._check_cost_limits(provider)

        # Rate limiting
        await self._rate_limit(provider, config.rpm_limit)

        # Execute API call
        try:
            result = await api_func()

            # Track cost
            cost = self._calculate_cost(
                config,
                input_tokens,
                output_tokens
            )

            self._record_cost(provider, cost)

            return result

        except Exception as e:
            print(f"❌ API call to {provider} failed: {e}")
            raise

    async def _rate_limit(self, provider: str, rpm_limit: int):
        """
        Enforce rate limiting using sliding window

        Args:
            provider: API provider name
            rpm_limit: Requests per minute limit
        """
        now = time.time()
        request_times = self.api_request_times[provider]

        # Remove requests older than 1 minute
        cutoff_time = now - 60
        request_times[:] = [t for t in request_times if t > cutoff_time]

        # Check if we're at the limit
        while len(request_times) >= rpm_limit:
            # Wait until oldest request is more than 1 minute old
            oldest = request_times[0]
            wait_time = 60 - (now - oldest) + 0.1  # Add small buffer
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = time.time()
                request_times[:] = [t for t in request_times if t > now - 60]
            else:
                break

        # Record this request
        request_times.append(now)

    async def _check_cost_limits(self, provider: str):
        """Check if we've exceeded cost limits"""
        # Check provider-specific limit
        config = self.api_providers[provider]
        if config.daily_limit is not None:
            if self.costs[provider] >= config.daily_limit:
                raise Exception(
                    f"Daily cost limit reached for {provider}: "
                    f"${self.costs[provider]:.2f} / ${config.daily_limit:.2f}"
                )

        # Check global limit
        total_cost = sum(self.costs.values())
        if total_cost >= self.global_daily_limit:
            raise Exception(
                f"Global daily cost limit reached: "
                f"${total_cost:.2f} / ${self.global_daily_limit:.2f}"
            )

    def _calculate_cost(
        self,
        config: APIProviderConfig,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost for API call"""
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output
        return input_cost + output_cost

    def _record_cost(self, provider: str, cost: float):
        """Record cost for tracking"""
        self.costs[provider] += cost
        self.cost_history.append((time.time(), provider, cost))

    def get_status(self) -> Dict[str, Any]:
        """Get current resource status"""
        status = {
            "cpu": {
                "total_cores": self.cpu_cores,
                "available": self.cpu_semaphore._value,
                "in_use": self.cpu_active
            },
            "costs": {
                "by_provider": self.costs,
                "total": sum(self.costs.values()),
                "global_limit": self.global_daily_limit,
                "remaining": self.global_daily_limit - sum(self.costs.values())
            },
            "api_rate_limits": {
                provider: {
                    "rpm_limit": config.rpm_limit,
                    "recent_requests": len(self.api_request_times[provider]),
                    "available": config.rpm_limit - len(self.api_request_times[provider])
                }
                for provider, config in self.api_providers.items()
            }
        }

        if self.gpu_available:
            status["gpu"] = {
                "available": True,
                "active": self.gpu_active,
                "queue_size": self.gpu_queue.qsize(),
                "current_task": self.gpu_current_task
            }
        else:
            status["gpu"] = {"available": False}

        return status

    def reset_daily_costs(self):
        """Reset daily cost tracking (call at midnight)"""
        self.costs = {provider: 0.0 for provider in self.api_providers.keys()}
        self.cost_history = []
        print("🔄 Daily costs reset")

    async def wait_for_gpu_available(self, timeout: float = 300) -> bool:
        """
        Wait until GPU becomes available

        Args:
            timeout: Maximum seconds to wait

        Returns:
            True if GPU became available, False if timeout
        """
        if not self.gpu_available:
            return False

        start_time = time.time()
        while self.gpu_active:
            if time.time() - start_time > timeout:
                return False
            await asyncio.sleep(1)

        return True

    def get_cost_report(self) -> Dict[str, Any]:
        """Get detailed cost report"""
        total = sum(self.costs.values())

        return {
            "total_cost": total,
            "by_provider": self.costs,
            "percent_of_limit": (total / self.global_daily_limit) * 100,
            "limit_remaining": self.global_daily_limit - total,
            "transaction_count": len(self.cost_history),
            "most_expensive_provider": max(
                self.costs.items(),
                key=lambda x: x[1]
            )[0] if self.costs else None
        }
