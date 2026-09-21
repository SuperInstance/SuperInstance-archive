#!/usr/bin/env python3
"""
Enhanced Multi-Bot Orchestration System
Complete integration of all orchestration components
"""

import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from director.enhanced_claude_director import EnhancedClaudeDirector, EnhancedTaskResult
from engines.task_decomposition_engine import TaskDecompositionEngine, TaskAnalysis
from engines.bot_allocation_intelligence import BotAllocationIntelligence, AllocationConstraints
from integrations.local_llm_connector import LocalLLMConnector
from reporting.progress_reporter import ProgressReporter, ReportType
from reporting.web_dashboard import WebDashboard
from director.claude_director import Task, TaskPriority, TaskStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/enhanced-orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedBotOrchestrator:
    """Enhanced multi-bot orchestration system with full integration"""
    
    def __init__(
        self,
        claude_api_key: str,
        bot_ecosystem_url: str = "http://localhost:8450",
        dashboard_port: int = 8481
    ):
        self.claude_api_key = claude_api_key
        self.bot_ecosystem_url = bot_ecosystem_url
        self.dashboard_port = dashboard_port
        
        # Initialize components
        self.local_llm_connector = LocalLLMConnector(bot_ecosystem_url)
        self.director = EnhancedClaudeDirector(claude_api_key, bot_ecosystem_url)
        self.decomposition_engine = None  # Will be initialized after director starts
        self.allocation_intelligence = BotAllocationIntelligence(self.local_llm_connector)
        self.progress_reporter = ProgressReporter()
        self.web_dashboard = WebDashboard(self.progress_reporter, dashboard_port)
        
        # System state
        self.running = False
        self.active_tasks: Dict[str, Task] = {}
        self.system_metrics = {
            "start_time": datetime.now(),
            "total_tasks_processed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_cost": 0.0,
            "cost_saved": 0.0
        }
        
    async def start(self):
        """Start the enhanced orchestration system"""
        logger.info("Starting Enhanced Multi-Bot Orchestration System...")
        
        try:
            # Start core components
            await self.director.start()
            
            # Initialize decomposition engine after director is ready
            self.decomposition_engine = TaskDecompositionEngine(
                self.director.claude_api,
                self.local_llm_connector
            )
            
            logger.info("All core components started successfully")
            
            # Start web dashboard in background
            asyncio.create_task(self._start_dashboard())
            
            # Start background monitoring
            asyncio.create_task(self._background_monitoring())
            
            self.running = True
            logger.info("Enhanced Bot Orchestration System fully operational")
            
            # Display system information
            await self._display_startup_info()
            
        except Exception as e:
            logger.error(f"Failed to start orchestration system: {e}")
            raise
    
    async def stop(self):
        """Stop the orchestration system"""
        logger.info("Stopping Enhanced Multi-Bot Orchestration System...")
        
        self.running = False
        
        # Stop components
        if self.director:
            await self.director.stop()
        
        logger.info("Enhanced Bot Orchestration System stopped")
    
    async def submit_task(
        self,
        description: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        estimated_tokens: int = 2000,
        constraints: Optional[AllocationConstraints] = None,
        strategy: str = "balanced"
    ) -> str:
        """Submit a new task for orchestrated execution"""
        
        # Create task
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_tasks)}"
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            estimated_tokens=estimated_tokens,
            status=TaskStatus.PENDING
        )
        
        self.active_tasks[task_id] = task
        logger.info(f"Task submitted: {task_id} - {description[:50]}...")
        
        # Start task processing in background
        asyncio.create_task(self._process_task(task, constraints, strategy))
        
        return task_id
    
    async def _process_task(
        self,
        task: Task,
        constraints: Optional[AllocationConstraints],
        strategy: str
    ):
        """Process a task through the complete orchestration pipeline"""
        
        try:
            # Step 1: Start progress tracking
            await self.progress_reporter.track_task(task)
            
            # Step 2: Analyze and potentially decompose the task
            analysis = await self.decomposition_engine.analyze_task(task)
            logger.info(f"Task {task.id} analysis: {analysis.complexity.name} complexity, {analysis.estimated_steps} steps")
            
            # Step 3: Decompose if needed
            if analysis.complexity.value > 2:  # More than simple
                decomposition_result = await self.decomposition_engine.decompose_task(task)
                await self.progress_reporter.track_task(task, decomposition_result)
                
                if len(decomposition_result.subtasks) > 1:
                    # Process subtasks
                    return await self._process_decomposed_task(task, decomposition_result, constraints, strategy)
            
            # Step 4: Allocate bot for single task
            allocation = await self.allocation_intelligence.allocate_bot(task, constraints, strategy)
            if not allocation:
                await self._handle_task_failure(task, "No suitable bot available")
                return
            
            await self.progress_reporter.track_bot_allocation(task.id, allocation)
            
            # Step 5: Execute task
            result = await self.director.execute_task(task.id)
            
            # Step 6: Update metrics and progress
            await self._handle_task_completion(task, result, allocation.allocated_bot_id)
            
        except Exception as e:
            logger.error(f"Task processing failed for {task.id}: {e}")
            await self._handle_task_failure(task, str(e))
    
    async def _process_decomposed_task(
        self,
        parent_task: Task,
        decomposition_result,
        constraints: Optional[AllocationConstraints],
        strategy: str
    ) -> bool:
        """Process a task that has been decomposed into subtasks"""
        
        logger.info(f"Processing decomposed task {parent_task.id} with {len(decomposition_result.subtasks)} subtasks")
        
        # Update task status
        parent_task.status = TaskStatus.IN_PROGRESS
        await self.progress_reporter.update_task_status(parent_task.id, TaskStatus.IN_PROGRESS)
        
        subtask_results = []
        
        try:
            # Execute subtasks according to execution plan
            execution_plan = decomposition_result.execution_plan
            
            if execution_plan.get("strategy") == "sequential":
                # Sequential execution
                for subtask in decomposition_result.subtasks:
                    result = await self._execute_subtask(subtask, constraints, strategy)
                    subtask_results.append(result)
                    
                    if result["success"]:
                        await self.progress_reporter.track_subtask_completion(parent_task.id, subtask.id)
                    else:
                        # Subtask failed, decide whether to continue or abort
                        if subtask.risk_level > 0.7:
                            logger.error(f"High-risk subtask {subtask.id} failed, aborting parent task")
                            await self._handle_task_failure(parent_task, f"Critical subtask {subtask.id} failed")
                            return False
                        else:
                            logger.warning(f"Subtask {subtask.id} failed but continuing with others")
            
            elif execution_plan.get("strategy") == "hybrid":
                # Hybrid execution with parallel groups and sequential tasks
                
                # Execute parallel groups first
                for parallel_group in execution_plan.get("parallel_groups", []):
                    parallel_tasks = []
                    for subtask_id in parallel_group:
                        subtask = next(st for st in decomposition_result.subtasks if st.id == subtask_id)
                        parallel_tasks.append(self._execute_subtask(subtask, constraints, strategy))
                    
                    # Wait for all parallel tasks to complete
                    parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(parallel_results):
                        if isinstance(result, Exception):
                            logger.error(f"Parallel subtask failed: {result}")
                            subtask_results.append({"success": False, "error": str(result)})
                        else:
                            subtask_results.append(result)
                            if result["success"]:
                                subtask_id = parallel_group[i]
                                await self.progress_reporter.track_subtask_completion(parent_task.id, subtask_id)
                
                # Then execute sequential tasks
                for subtask_id in execution_plan.get("sequential_tasks", []):
                    subtask = next(st for st in decomposition_result.subtasks if st.id == subtask_id)
                    result = await self._execute_subtask(subtask, constraints, strategy)
                    subtask_results.append(result)
                    
                    if result["success"]:
                        await self.progress_reporter.track_subtask_completion(parent_task.id, subtask.id)
            
            # Evaluate overall success
            successful_subtasks = sum(1 for result in subtask_results if result.get("success", False))
            success_rate = successful_subtasks / len(subtask_results)
            
            if success_rate >= 0.8:  # 80% success threshold
                parent_task.status = TaskStatus.COMPLETED
                await self.progress_reporter.update_task_status(parent_task.id, TaskStatus.COMPLETED)
                
                # Calculate combined metrics
                total_cost = sum(result.get("cost", 0) for result in subtask_results)
                avg_quality = sum(result.get("quality_score", 0.8) for result in subtask_results) / len(subtask_results)
                
                await self.progress_reporter.track_performance_metrics(parent_task.id, {
                    "cost": total_cost,
                    "quality_score": avg_quality,
                    "subtasks_completed": successful_subtasks,
                    "subtasks_total": len(subtask_results),
                    "success_rate": success_rate
                })
                
                self.system_metrics["successful_tasks"] += 1
                self.system_metrics["total_cost"] += total_cost
                
                logger.info(f"Decomposed task {parent_task.id} completed successfully ({success_rate:.1%} subtask success)")
                return True
            else:
                await self._handle_task_failure(parent_task, f"Insufficient subtask success rate: {success_rate:.1%}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing decomposed task {parent_task.id}: {e}")
            await self._handle_task_failure(parent_task, str(e))
            return False
    
    async def _execute_subtask(self, subtask, constraints: Optional[AllocationConstraints], strategy: str) -> Dict[str, Any]:
        """Execute a single subtask"""
        
        # Create temporary task for subtask execution
        temp_task = Task(
            id=subtask.id,
            description=subtask.description,
            priority=TaskPriority.MEDIUM,  # Subtasks are usually medium priority
            estimated_tokens=subtask.estimated_tokens,
            status=TaskStatus.PENDING
        )
        
        # Apply subtask-specific constraints
        subtask_constraints = constraints or AllocationConstraints()
        if subtask.preferred_model_type == "local":
            subtask_constraints.require_local = True
        elif subtask.preferred_model_type.startswith("claude"):
            subtask_constraints.preferred_providers = ["anthropic"]
        
        # Allocate bot
        allocation = await self.allocation_intelligence.allocate_bot(temp_task, subtask_constraints, strategy)
        if not allocation:
            return {
                "success": False,
                "error": "No suitable bot available for subtask",
                "cost": 0,
                "subtask_id": subtask.id
            }
        
        try:
            # Execute subtask using the director
            result = await self.director.execute_task(subtask.id)
            
            # Release bot
            await self.allocation_intelligence.release_bot(allocation.allocated_bot_id)
            
            # Update bot performance metrics
            await self.allocation_intelligence.update_bot_performance(
                allocation.allocated_bot_id,
                {
                    "success": result.success,
                    "latency_ms": result.latency_ms,
                    "cost": result.cost,
                    "quality_score": result.confidence_score or 0.8
                }
            )
            
            return {
                "success": result.success,
                "response": result.response,
                "error": result.error,
                "cost": result.cost,
                "latency_ms": result.latency_ms,
                "model_used": result.model_used,
                "quality_score": result.confidence_score or 0.8,
                "subtask_id": subtask.id
            }
            
        except Exception as e:
            await self.allocation_intelligence.release_bot(allocation.allocated_bot_id)
            return {
                "success": False,
                "error": str(e),
                "cost": 0,
                "subtask_id": subtask.id
            }
    
    async def _handle_task_completion(self, task: Task, result: EnhancedTaskResult, bot_id: str):
        """Handle successful task completion"""
        
        task.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        await self.progress_reporter.update_task_status(
            task.id, 
            task.status,
            {
                "cost": result.cost,
                "latency_ms": result.latency_ms,
                "model_used": result.model_used,
                "confidence_score": result.confidence_score
            }
        )
        
        # Update performance metrics
        await self.progress_reporter.track_performance_metrics(task.id, {
            "cost": result.cost,
            "tokens_used": len(result.response.split()) * 4 if result.response else 0,
            "quality_score": result.confidence_score,
            "retry_count": result.total_attempts - 1
        })
        
        # Update bot performance
        await self.allocation_intelligence.update_bot_performance(bot_id, {
            "success": result.success,
            "latency_ms": result.latency_ms,
            "cost": result.cost,
            "quality_score": result.confidence_score or 0.8
        })
        
        # Release bot
        await self.allocation_intelligence.release_bot(bot_id)
        
        # Update system metrics
        self.system_metrics["total_tasks_processed"] += 1
        if result.success:
            self.system_metrics["successful_tasks"] += 1
        else:
            self.system_metrics["failed_tasks"] += 1
        
        self.system_metrics["total_cost"] += result.cost
        
        if result.is_local and not result.fallback_used:
            # Estimate cost savings from using local models
            estimated_claude_cost = (task.estimated_tokens / 1000) * 0.003  # Rough estimate
            self.system_metrics["cost_saved"] += estimated_claude_cost
        
        # Remove from active tasks
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        
        logger.info(f"Task {task.id} {'completed' if result.success else 'failed'}: cost=${result.cost:.4f}, {result.latency_ms:.0f}ms")
    
    async def _handle_task_failure(self, task: Task, error: str):
        """Handle task failure"""
        
        task.status = TaskStatus.FAILED
        task.error_message = error
        
        await self.progress_reporter.update_task_status(task.id, TaskStatus.FAILED, {"error": error})
        
        self.system_metrics["total_tasks_processed"] += 1
        self.system_metrics["failed_tasks"] += 1
        
        # Remove from active tasks
        if task.id in self.active_tasks:
            del self.active_tasks[task.id]
        
        logger.error(f"Task {task.id} failed: {error}")
    
    async def _start_dashboard(self):
        """Start the web dashboard"""
        try:
            await self.web_dashboard.start()
        except Exception as e:
            logger.error(f"Failed to start web dashboard: {e}")
    
    async def _background_monitoring(self):
        """Background monitoring and maintenance tasks"""
        
        while self.running:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Update system metrics
                await self._update_system_metrics()
                
                # Generate periodic reports
                if datetime.now().minute % 15 == 0:  # Every 15 minutes
                    await self._generate_periodic_reports()
                
                # Cleanup old data
                if datetime.now().hour % 6 == 0 and datetime.now().minute == 0:  # Every 6 hours
                    await self._cleanup_old_data()
                    
            except Exception as e:
                logger.error(f"Background monitoring error: {e}")
    
    async def _update_system_metrics(self):
        """Update system performance metrics"""
        
        # Get bot statistics
        bot_stats = self.allocation_intelligence.get_bot_stats()
        
        # Get allocation analytics
        allocation_analytics = self.allocation_intelligence.get_allocation_analytics()
        
        # Update metrics
        self.system_metrics.update({
            "active_tasks": len(self.active_tasks),
            "available_bots": bot_stats["available_bots"],
            "current_bot_load": bot_stats["current_load"],
            "bot_utilization": (bot_stats["current_load"] / max(1, bot_stats["total_capacity"])) * 100,
            "recent_allocations": allocation_analytics.get("recent_allocations_24h", 0),
            "avg_allocation_confidence": allocation_analytics.get("avg_confidence", 0.0)
        })
    
    async def _generate_periodic_reports(self):
        """Generate periodic system reports"""
        
        try:
            # Generate executive summary
            exec_report = await self.progress_reporter.generate_report(ReportType.EXECUTIVE)
            logger.info(f"System Status - Completed today: {exec_report['summary']['completed_today']}, "
                       f"Success rate: {exec_report['summary']['success_rate']}%, "
                       f"Cost today: ${exec_report['summary']['cost_today']:.2f}")
            
            # Check for alerts
            alerts = exec_report.get("alerts", [])
            for alert in alerts:
                if alert["level"] == "warning":
                    logger.warning(f"System Alert: {alert['message']}")
                elif alert["level"] == "critical":
                    logger.error(f"Critical Alert: {alert['message']}")
                    
        except Exception as e:
            logger.error(f"Failed to generate periodic reports: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data to prevent memory bloat"""
        
        logger.info("Performing system cleanup...")
        
        # This would normally clean up old progress data, logs, etc.
        # Implementation would depend on specific storage mechanisms
        
        logger.info("System cleanup completed")
    
    async def _display_startup_info(self):
        """Display system startup information"""
        
        bot_stats = self.allocation_intelligence.get_bot_stats()
        
        print("\n" + "="*60)
        print("Enhanced Multi-Bot Orchestration System - READY")
        print("="*60)
        print(f"Director Terminal: http://localhost:8480")
        print(f"Progress Dashboard: http://localhost:{self.dashboard_port}")
        print(f"Bot Ecosystem API: {self.bot_ecosystem_url}")
        print()
        print(f"Available Bots: {bot_stats['available_bots']}/{bot_stats['total_bots']}")
        print(f"Total Capacity: {bot_stats['total_capacity']} concurrent tasks")
        print(f"Local LLM Status: {'Connected' if self.local_llm_connector.connected else 'Offline'}")
        print()
        print("System Features:")
        print("✓ Intelligent task decomposition")
        print("✓ Smart bot allocation")
        print("✓ Cost optimization with local LLMs") 
        print("✓ Real-time progress tracking")
        print("✓ Performance analytics")
        print("✓ Web dashboard monitoring")
        print("="*60)
        print()
    
    # Public API methods
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        
        bot_stats = self.allocation_intelligence.get_bot_stats()
        allocation_analytics = self.allocation_intelligence.get_allocation_analytics()
        system_overview = self.progress_reporter.get_system_overview()
        
        return {
            "system_info": {
                "running": self.running,
                "start_time": self.system_metrics["start_time"].isoformat(),
                "uptime_hours": (datetime.now() - self.system_metrics["start_time"]).total_seconds() / 3600
            },
            "task_metrics": {
                "active_tasks": len(self.active_tasks),
                "total_processed": self.system_metrics["total_tasks_processed"],
                "successful": self.system_metrics["successful_tasks"],
                "failed": self.system_metrics["failed_tasks"],
                "success_rate": (self.system_metrics["successful_tasks"] / 
                               max(1, self.system_metrics["total_tasks_processed"])) * 100
            },
            "bot_metrics": bot_stats,
            "cost_metrics": {
                "total_cost": self.system_metrics["total_cost"],
                "cost_saved": self.system_metrics["cost_saved"],
                "avg_cost_per_task": (self.system_metrics["total_cost"] / 
                                    max(1, self.system_metrics["total_tasks_processed"]))
            },
            "allocation_analytics": allocation_analytics,
            "progress_overview": system_overview
        }
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        return self.progress_reporter.get_progress_summary(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task"""
        
        if task_id not in self.active_tasks:
            return False
        
        task = self.active_tasks[task_id]
        task.status = TaskStatus.CANCELLED
        
        await self.progress_reporter.update_task_status(task_id, TaskStatus.CANCELLED)
        
        del self.active_tasks[task_id]
        
        logger.info(f"Task {task_id} cancelled")
        return True

# Main execution
async def main():
    """Main entry point"""
    
    # Check for API key
    claude_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not claude_api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is required")
        sys.exit(1)
    
    # Create and start orchestrator
    orchestrator = EnhancedBotOrchestrator(claude_api_key)
    
    try:
        await orchestrator.start()
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs("/home/activeloguser/activelog/logs", exist_ok=True)
    
    # Run the orchestrator
    asyncio.run(main())