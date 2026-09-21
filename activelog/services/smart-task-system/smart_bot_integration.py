#!/usr/bin/env python3
"""
Smart Bot Integration System
Integrates intelligent task classification with existing bot infrastructure
Automatically routes tasks to optimal Claude models
"""

import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict
import aiohttp
from task_intelligence import (
    TaskIntelligenceClassifier, SmartTaskQueue, 
    ModelTier, TaskComplexity, MODEL_CONFIGS
)

logger = logging.getLogger(__name__)

class SmartBotRouter:
    """Routes tasks to appropriate Claude models based on intelligence analysis"""
    
    def __init__(self, anthropic_api_key: str, orchestrator_url: str = None):
        self.anthropic_api_key = anthropic_api_key
        self.orchestrator_url = orchestrator_url
        self.classifier = TaskIntelligenceClassifier()
        self.task_queue = SmartTaskQueue()
        self.session = None
        
        # Performance tracking
        self.model_performance = {
            tier: {
                "tasks_completed": 0,
                "total_cost": 0.0,
                "average_time": 0.0,
                "success_rate": 1.0,
                "total_tokens": 0
            }
            for tier in ModelTier
        }
        
        # Smart routing rules
        self.routing_rules = {
            "cost_optimization_threshold": 0.50,  # Switch to cheaper model if cost > $0.50
            "time_critical_model_upgrade": True,   # Upgrade model for urgent tasks
            "batch_processing_optimization": True,  # Group similar tasks
            "adaptive_learning": True               # Learn from task outcomes
        }
        
    async def start(self):
        """Initialize the smart routing system"""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.anthropic_api_key}"}
        )
        logger.info("Smart bot router initialized")
        
    async def stop(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        logger.info("Smart bot router stopped")
        
    async def submit_smart_task(self, description: str, context: str = "", 
                               priority: str = "MEDIUM", files: List[str] = None,
                               user_id: str = "system") -> Dict[str, Any]:
        """Submit task with automatic model selection and optimization"""
        
        # Add to smart queue for analysis
        task_id = self.task_queue.add_task(description, context, priority, files)
        task = self.task_queue.tasks[task_id]
        analysis = task["analysis"]
        
        logger.info(f"Smart task submitted: {task_id}")
        logger.info(f"  Model: {analysis['recommended_model']} ({analysis['confidence']:.1%})")
        logger.info(f"  Complexity: {analysis['complexity']}")
        logger.info(f"  Estimated cost: ${analysis['estimated_cost']:.4f}")
        
        # Execute task with selected model
        result = await self._execute_task_with_model(task_id, task)
        
        return {
            "task_id": task_id,
            "analysis": analysis,
            "execution_result": result,
            "optimization_summary": self._get_optimization_summary(task)
        }
        
    async def _execute_task_with_model(self, task_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using the recommended model"""
        
        analysis = task["analysis"]
        model_tier = ModelTier(analysis["recommended_model"])
        model_config = MODEL_CONFIGS[model_tier]
        
        # Build optimized prompt based on task complexity
        prompt = self._build_optimized_prompt(task, model_tier)
        
        start_time = time.time()
        
        try:
            # Execute with selected Claude model
            response = await self._call_claude_api(
                model=model_config.model_name,
                prompt=prompt,
                max_tokens=min(analysis["estimated_output_tokens"] + 500, model_config.max_tokens)
            )
            
            execution_time = time.time() - start_time
            
            # Update task status
            self.task_queue.tasks[task_id]["status"] = "completed"
            self.task_queue.tasks[task_id]["completed_at"] = datetime.now().isoformat()
            self.task_queue.tasks[task_id]["execution_time"] = execution_time
            
            # Update performance metrics
            self._update_model_performance(model_tier, response, execution_time, success=True)
            
            # Log to micro_updates.log in SuperInstance format
            await self._log_superinstance_activity(task_id, task, "COMPLETE", execution_time)
            
            return {
                "status": "success",
                "content": response.get("content", [{}])[0].get("text", ""),
                "model_used": model_config.model_name,
                "actual_cost": response.get("actual_cost", 0.0),
                "execution_time": execution_time,
                "tokens_used": response.get("usage", {})
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Update task as failed
            self.task_queue.tasks[task_id]["status"] = "failed"
            self.task_queue.tasks[task_id]["error"] = str(e)
            
            # Update performance metrics
            self._update_model_performance(model_tier, {}, execution_time, success=False)
            
            # Log failure
            await self._log_superinstance_activity(task_id, task, "FAILED", execution_time)
            
            logger.error(f"Task {task_id} failed: {e}")
            
            return {
                "status": "failed",
                "error": str(e),
                "model_used": model_config.model_name,
                "execution_time": execution_time
            }
            
    def _build_optimized_prompt(self, task: Dict[str, Any], model_tier: ModelTier) -> str:
        """Build optimized prompt based on model capabilities"""
        
        description = task["description"]
        context = task.get("context", "")
        files = task.get("files", [])
        analysis = task["analysis"]
        
        # Base SuperInstance bot identity
        base_prompt = f"""You are a SuperInstance bot specialized in building cloud server infrastructure superior to local servers.

TASK CLASSIFICATION: {analysis['complexity']} complexity, {model_tier.value} model selected
CATEGORIES: {', '.join(analysis['task_categories'])}
REASONING: {analysis['reasoning']}

MISSION CONTEXT:
- Building ActiveLog fitness tracking with AI-powered cross-domain intelligence
- Infrastructure ready, Services 70% complete, Domains 40% complete
- Focus on token efficiency and practical solutions

TASK: {description}"""

        if context:
            base_prompt += f"\n\nCONTEXT:\n{context}"
            
        # Adjust prompt style based on model capabilities
        if model_tier == ModelTier.HAIKU:
            # Concise, direct prompts for Haiku
            base_prompt += "\n\nProvide a concise, direct solution. Focus on efficiency and clarity."
            
        elif model_tier == ModelTier.SONNET:
            # Balanced prompts for Sonnet  
            base_prompt += "\n\nProvide a thorough solution with clear implementation steps. Include error handling and best practices."
            
        elif model_tier == ModelTier.OPUS:
            # Comprehensive prompts for Opus
            base_prompt += f"""

ADVANCED ANALYSIS REQUIRED:
- Consider multiple approaches and trade-offs
- Provide architectural insights and long-term implications  
- Include scalability and maintainability considerations
- Explain reasoning for complex decisions

This task requires {analysis['complexity']} level thinking because: {analysis['reasoning']}"""

        # Add file context if relevant
        if files:
            base_prompt += f"\n\nFILES TO CONSIDER: {', '.join(files)}"
            
        # Add SuperInstance specific guidance
        if analysis["requires_reasoning"]:
            base_prompt += "\n\nUSE ADVANCED REASONING: Apply systems thinking and consider interdependencies."
            
        if analysis["requires_creativity"]:
            base_prompt += "\n\nCREATIVE SOLUTION NEEDED: Think innovatively while maintaining SuperInstance excellence."
            
        if analysis["is_time_sensitive"]:
            base_prompt += "\n\nTIME CRITICAL: Prioritize speed while maintaining quality."
            
        return base_prompt
        
    async def _call_claude_api(self, model: str, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Call Claude API with specified model"""
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        
        async with self.session.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        ) as response:
            
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Claude API error ({response.status}): {error_text}")
                
            result = await response.json()
            
            # Calculate actual cost
            usage = result.get('usage', {})
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            
            # Get model pricing
            model_tier = None
            for tier, config in MODEL_CONFIGS.items():
                if config.model_name == model:
                    model_tier = tier
                    break
                    
            if model_tier:
                config = MODEL_CONFIGS[model_tier]
                actual_cost = (
                    (input_tokens / 1000) * config.cost_per_1k_input +
                    (output_tokens / 1000) * config.cost_per_1k_output
                )
                result["actual_cost"] = actual_cost
                
            return result
            
    def _update_model_performance(self, model_tier: ModelTier, response: Dict, 
                                 execution_time: float, success: bool):
        """Update performance tracking for model"""
        
        perf = self.model_performance[model_tier]
        
        # Update counters
        perf["tasks_completed"] += 1
        
        if success:
            # Update cost tracking
            actual_cost = response.get("actual_cost", 0.0)
            perf["total_cost"] += actual_cost
            
            # Update token usage
            usage = response.get("usage", {})
            total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            perf["total_tokens"] += total_tokens
            
            # Update timing
            perf["average_time"] = (perf["average_time"] + execution_time) / 2
            
        # Update success rate (exponential moving average)
        success_rate = 1.0 if success else 0.0
        perf["success_rate"] = perf["success_rate"] * 0.9 + success_rate * 0.1
        
    async def _log_superinstance_activity(self, task_id: str, task: Dict[str, Any], 
                                         action: str, execution_time: float):
        """Log activity to SuperInstance micro_updates.log"""
        
        try:
            timestamp = datetime.now().strftime('%H:%M')
            analysis = task["analysis"]
            model = analysis["recommended_model"]
            
            # Create concise log entry
            task_desc = task["description"][:50] + "..." if len(task["description"]) > 50 else task["description"]
            
            log_entry = f"{timestamp}|smart-bot-{model}|{action}|{task_desc}|{execution_time:.1f}s|${analysis['estimated_cost']:.4f}\n"
            
            # Append to micro_updates.log
            log_path = "/home/activeloguser/activelog/micro_updates.log"
            with open(log_path, "a") as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log SuperInstance activity: {e}")
            
    def _get_optimization_summary(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get optimization summary for task"""
        
        analysis = task["analysis"]
        
        # Calculate potential savings from smart routing
        opus_config = MODEL_CONFIGS[ModelTier.OPUS]
        selected_config = MODEL_CONFIGS[ModelTier(analysis["recommended_model"])]
        
        opus_cost = (
            (analysis["estimated_input_tokens"] / 1000) * opus_config.cost_per_1k_input +
            (analysis["estimated_output_tokens"] / 1000) * opus_config.cost_per_1k_output
        )
        
        cost_savings = opus_cost - analysis["estimated_cost"]
        savings_percentage = (cost_savings / opus_cost) * 100 if opus_cost > 0 else 0
        
        return {
            "model_selected": analysis["recommended_model"],
            "confidence": analysis["confidence"],
            "estimated_cost": analysis["estimated_cost"],
            "opus_cost": opus_cost,
            "cost_savings": cost_savings,
            "savings_percentage": savings_percentage,
            "complexity_detected": analysis["complexity"],
            "optimization_reasoning": analysis["reasoning"]
        }
        
    async def process_batch_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple tasks with batch optimization"""
        
        logger.info(f"Processing batch of {len(tasks)} tasks")
        
        results = []
        
        # Analyze all tasks first
        analyses = self.classifier.batch_analyze_tasks(tasks)
        
        # Optimize distribution across models
        distribution = self.classifier.optimize_task_distribution(analyses)
        
        # Process tasks by model tier for efficiency
        for model_tier in ModelTier:
            task_indices = distribution[model_tier]
            if not task_indices:
                continue
                
            logger.info(f"Processing {len(task_indices)} tasks with {model_tier.value}")
            
            # Process tasks in parallel for same model
            batch_tasks = []
            for i in task_indices:
                task_data = tasks[i]
                task_id = self.task_queue.add_task(**task_data)
                batch_tasks.append((task_id, self.task_queue.tasks[task_id]))
                
            # Execute batch
            batch_results = await asyncio.gather(*[
                self._execute_task_with_model(task_id, task)
                for task_id, task in batch_tasks
            ], return_exceptions=True)
            
            # Collect results
            for (task_id, task), result in zip(batch_tasks, batch_results):
                if isinstance(result, Exception):
                    result = {"status": "failed", "error": str(result)}
                    
                results.append({
                    "task_id": task_id,
                    "analysis": task["analysis"],
                    "result": result
                })
                
        return results
        
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        
        total_tasks = sum(perf["tasks_completed"] for perf in self.model_performance.values())
        total_cost = sum(perf["total_cost"] for perf in self.model_performance.values())
        
        # Calculate efficiency metrics
        model_efficiency = {}
        for tier, perf in self.model_performance.items():
            if perf["tasks_completed"] > 0:
                avg_cost = perf["total_cost"] / perf["tasks_completed"]
                avg_time = perf["average_time"]
                
                model_efficiency[tier.value] = {
                    "tasks_completed": perf["tasks_completed"],
                    "success_rate": perf["success_rate"],
                    "average_cost_per_task": avg_cost,
                    "average_execution_time": avg_time,
                    "total_cost": perf["total_cost"],
                    "total_tokens": perf["total_tokens"],
                    "cost_efficiency_score": 1.0 / (avg_cost + 0.001),  # Higher is better
                    "time_efficiency_score": 1.0 / (avg_time + 0.1)     # Higher is better
                }
                
        # Queue statistics
        queue_summary = self.task_queue.get_queue_summary()
        
        return {
            "performance_summary": {
                "total_tasks_processed": total_tasks,
                "total_cost": total_cost,
                "average_cost_per_task": total_cost / max(total_tasks, 1)
            },
            "model_performance": model_efficiency,
            "queue_status": queue_summary,
            "optimization_rules": self.routing_rules
        }

# Integration with existing SuperInstance infrastructure
class SuperInstanceSmartBotManager:
    """Manages smart bots within SuperInstance ecosystem"""
    
    def __init__(self, anthropic_api_key: str, orchestrator_url: str = None, 
                 redis_url: str = "redis://localhost:6379"):
        self.smart_router = SmartBotRouter(anthropic_api_key, orchestrator_url)
        self.redis_url = redis_url
        
    async def start_smart_processing(self):
        """Start smart bot processing system"""
        await self.smart_router.start()
        
        # Start background task to monitor micro_updates.log for new tasks
        asyncio.create_task(self._monitor_micro_updates())
        
        # Start background task to process task files
        asyncio.create_task(self._monitor_task_files())
        
        logger.info("SuperInstance smart bot management started")
        
    async def _monitor_micro_updates(self):
        """Monitor micro_updates.log for task assignments"""
        
        log_path = "/home/activeloguser/activelog/micro_updates.log"
        last_position = 0
        
        while True:
            try:
                if os.path.exists(log_path):
                    with open(log_path, 'r') as f:
                        f.seek(last_position)
                        new_lines = f.readlines()
                        last_position = f.tell()
                        
                    # Process new task assignments
                    for line in new_lines:
                        if "|ASSIGN|" in line or "|URGENT|" in line:
                            await self._process_micro_update_task(line.strip())
                            
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring micro updates: {e}")
                await asyncio.sleep(30)
                
    async def _process_micro_update_task(self, log_line: str):
        """Process task from micro_updates.log entry"""
        
        try:
            parts = log_line.split("|")
            if len(parts) >= 4:
                timestamp = parts[0]
                bot_id = parts[1]
                action = parts[2]
                task_desc = parts[3]
                
                # Extract priority from action or description
                priority = "HIGH" if "URGENT" in action or "CRITICAL" in task_desc else "MEDIUM"
                
                # Submit as smart task
                result = await self.smart_router.submit_smart_task(
                    description=task_desc,
                    context=f"Task from micro_updates.log at {timestamp}",
                    priority=priority,
                    user_id=bot_id
                )
                
                logger.info(f"Processed micro update task: {result['task_id']}")
                
        except Exception as e:
            logger.error(f"Error processing micro update task: {e}")
            
    async def _monitor_task_files(self):
        """Monitor task assignment files"""
        
        task_files = [
            "/home/activeloguser/activelog/task_assignments_optimized.txt",
            "/home/activeloguser/activelog/DEVELOPMENT_TASK_MATRIX.md"
        ]
        
        file_positions = {file: 0 for file in task_files}
        
        while True:
            try:
                for file_path in task_files:
                    if os.path.exists(file_path):
                        current_size = os.path.getsize(file_path)
                        last_size = file_positions[file_path]
                        
                        if current_size > last_size:
                            # File has grown, read new content
                            with open(file_path, 'r') as f:
                                f.seek(last_size)
                                new_content = f.read()
                                file_positions[file_path] = current_size
                                
                            # Extract tasks from new content
                            await self._extract_tasks_from_content(new_content, file_path)
                            
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring task files: {e}")
                await asyncio.sleep(120)
                
    async def _extract_tasks_from_content(self, content: str, source_file: str):
        """Extract and process tasks from file content"""
        
        # Simple task extraction (can be made more sophisticated)
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Look for task indicators
            if (line.startswith('- ') or line.startswith('* ')) and len(line) > 10:
                # Extract priority from line
                priority = "MEDIUM"
                if "URGENT" in line or "CRITICAL" in line:
                    priority = "CRITICAL"
                elif "HIGH" in line:
                    priority = "HIGH"
                elif "LOW" in line:
                    priority = "LOW"
                    
                # Clean up task description
                task_desc = line.lstrip('- *').strip()
                task_desc = re.sub(r'(URGENT|CRITICAL|HIGH|MEDIUM|LOW):\s*', '', task_desc, flags=re.IGNORECASE)
                
                if len(task_desc) > 20:  # Only process substantial tasks
                    try:
                        result = await self.smart_router.submit_smart_task(
                            description=task_desc,
                            context=f"Task from {source_file}",
                            priority=priority
                        )
                        
                        logger.info(f"Processed file task: {result['task_id']}")
                        
                    except Exception as e:
                        logger.error(f"Error processing file task '{task_desc}': {e}")

# Example usage
if __name__ == "__main__":
    import sys
    import os
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)
        
    async def test_smart_routing():
        # Initialize smart bot system
        manager = SuperInstanceSmartBotManager(api_key)
        await manager.start_smart_processing()
        
        # Test with example tasks
        test_tasks = [
            {
                "description": "Fix typo in config file",
                "priority": "LOW"
            },
            {
                "description": "Implement Redis caching layer for fitness API endpoints",
                "context": "Need to reduce database load and improve response times",
                "priority": "HIGH"
            },
            {
                "description": "Research and design scalable architecture for real-time fitness data analytics",
                "context": "Handle millions of data points with advanced correlation analysis",
                "priority": "CRITICAL"
            }
        ]
        
        print("🧠 Testing Smart Task Routing...")
        
        for task in test_tasks:
            result = await manager.smart_router.submit_smart_task(**task)
            print(f"\n📋 Task: {task['description'][:50]}...")
            print(f"🤖 Model: {result['analysis']['recommended_model']}")
            print(f"💰 Cost: ${result['analysis']['estimated_cost']:.4f}")
            print(f"✅ Status: {result['execution_result']['status']}")
            
        # Show performance report
        report = manager.smart_router.get_performance_report()
        print(f"\n📊 Performance Report:")
        print(f"  Tasks processed: {report['performance_summary']['total_tasks_processed']}")
        print(f"  Total cost: ${report['performance_summary']['total_cost']:.4f}")
        
        await manager.smart_router.stop()
        
    # Run test
    asyncio.run(test_smart_routing())