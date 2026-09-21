#!/usr/bin/env python3
"""
Bot Learning Wrapper - Integrates learning system with existing bots
Automatically makes bots write learning journals after each task
"""

import asyncio
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from learning_engine import BotLearningOrchestrator, create_bot_learning_hook

logger = logging.getLogger(__name__)

class SmartBot:
    """Enhanced bot class with learning capabilities"""
    
    def __init__(self, bot_id: str, specialization: str, anthropic_api_key: str):
        self.bot_id = bot_id
        self.specialization = specialization
        self.api_key = anthropic_api_key
        self.learning_hook = create_bot_learning_hook()
        self.tasks_completed = 0
        self.total_learning_entries = 0
        
    async def execute_task_with_learning(self, task_description: str, 
                                       context: str = "") -> Dict[str, Any]:
        """Execute task and automatically record learning"""
        
        try:
            # Log task start
            await self._log_activity("START", task_description)
            
            # Execute the actual task (simplified for demo)
            result = await self._execute_task(task_description, context)
            
            # Record learning from this task
            learning_context = f"{context}\n\nTask execution result: {result['summary']}"
            self.learning_hook(self.bot_id, task_description, learning_context)
            
            # Log task completion
            await self._log_activity("COMPLETE", f"{task_description[:50]}...learning-recorded")
            
            self.tasks_completed += 1
            self.total_learning_entries += 1
            
            return {
                "status": "success",
                "task": task_description,
                "result": result,
                "learning_recorded": True,
                "bot_stats": {
                    "tasks_completed": self.tasks_completed,
                    "learning_entries": self.total_learning_entries
                }
            }
            
        except Exception as e:
            logger.error(f"Bot {self.bot_id} task failed: {e}")
            await self._log_activity("FAILED", f"{task_description[:50]}...error: {str(e)[:30]}")
            
            return {
                "status": "failed",
                "task": task_description,
                "error": str(e),
                "learning_recorded": False
            }
            
    async def _execute_task(self, task_description: str, context: str) -> Dict[str, Any]:
        """Execute the actual task (this would call Claude API in real implementation)"""
        
        # Simulate task execution with learning insights
        execution_time = 45  # seconds
        
        # Generate context-appropriate insights based on specialization
        insights = self._generate_execution_insights(task_description, context)
        
        return {
            "summary": f"Completed {task_description}",
            "execution_time": execution_time,
            "insights_gained": insights,
            "specialization_applied": self.specialization,
            "quality_score": 0.92,
            "ecosystem_understanding_improved": True
        }
        
    def _generate_execution_insights(self, task: str, context: str) -> Dict[str, Any]:
        """Generate execution insights based on bot specialization"""
        
        task_lower = task.lower()
        context_lower = context.lower()
        
        base_insights = {
            "superinstance_patterns_observed": [],
            "reusable_approaches": [],
            "integration_points_discovered": [],
            "optimization_opportunities": []
        }
        
        # Specialization-specific insights
        if self.specialization == "services":
            if "api" in task_lower:
                base_insights["superinstance_patterns_observed"].extend([
                    "FastAPI framework consistent across services",
                    "Pydantic models used for data validation",
                    "Async/await pattern for non-blocking operations"
                ])
                base_insights["reusable_approaches"].append("JWT authentication pattern reusable")
                
            if "database" in task_lower:
                base_insights["integration_points_discovered"].append("PostgreSQL with vector embeddings standard")
                base_insights["optimization_opportunities"].append("Redis caching layer reduces DB load by 60%+")
                
        elif self.specialization == "domains":
            if "dashboard" in task_lower or "interface" in task_lower:
                base_insights["superinstance_patterns_observed"].extend([
                    "React components with fitness-specific patterns",
                    "Responsive design critical for multi-device support",
                    "Real-time data integration via WebSocket connections"
                ])
                base_insights["reusable_approaches"].append("Fitness data visualization components highly reusable")
                
        elif self.specialization == "infrastructure":
            if "kubernetes" in task_lower or "monitoring" in task_lower:
                base_insights["superinstance_patterns_observed"].extend([
                    "Kubernetes manifest patterns consistent across services",
                    "Grafana dashboard templates reusable for different services",
                    "Prometheus metrics naming conventions established"
                ])
                base_insights["optimization_opportunities"].append("Container resource allocation can be optimized")
                
        elif self.specialization == "ai":
            if "analytics" in task_lower or "intelligence" in task_lower:
                base_insights["superinstance_patterns_observed"].extend([
                    "Claude API integration patterns for different complexity levels",
                    "Vector embedding storage in PostgreSQL for semantic search",
                    "Cross-domain correlation analysis requires specific data structures"
                ])
                base_insights["reusable_approaches"].append("AI model selection logic applicable across features")
                
        return base_insights
        
    async def _log_activity(self, action: str, description: str):
        """Log activity to micro_updates.log"""
        
        try:
            timestamp = datetime.now().strftime('%H:%M')
            log_entry = f"{timestamp}|{self.bot_id}|{action}|{description}\n"
            
            with open('/home/activeloguser/activelog/micro_updates.log', 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")

class BotFleet:
    """Manages a fleet of learning-enabled bots"""
    
    def __init__(self, anthropic_api_key: str):
        self.api_key = anthropic_api_key
        self.bots: Dict[str, SmartBot] = {}
        self.learning_orchestrator = BotLearningOrchestrator(anthropic_api_key)
        
    def create_bot(self, bot_id: str, specialization: str) -> SmartBot:
        """Create a new learning-enabled bot"""
        
        bot = SmartBot(bot_id, specialization, self.api_key)
        self.bots[bot_id] = bot
        
        logger.info(f"Created learning-enabled bot: {bot_id} ({specialization})")
        return bot
        
    async def deploy_bot_fleet(self) -> Dict[str, SmartBot]:
        """Deploy the standard SuperInstance bot fleet"""
        
        fleet = {
            "services-bot-001": self.create_bot("services-bot-001", "services"),
            "domains-bot-002": self.create_bot("domains-bot-002", "domains"), 
            "infra-bot-003": self.create_bot("infra-bot-003", "infrastructure"),
            "ai-bot-004": self.create_bot("ai-bot-004", "ai")
        }
        
        logger.info(f"Deployed bot fleet: {list(fleet.keys())}")
        return fleet
        
    async def start_learning_system(self):
        """Start the background learning system"""
        
        # Start the learning orchestrator
        asyncio.create_task(self.learning_orchestrator.start_learning_system())
        
        logger.info("Bot learning system started - synthesis every 15min, audit every hour")
        
    async def execute_fleet_tasks(self, task_assignments: Dict[str, str]) -> Dict[str, Any]:
        """Execute tasks across the bot fleet"""
        
        results = {}
        
        # Execute tasks in parallel
        tasks = []
        for bot_id, task_description in task_assignments.items():
            if bot_id in self.bots:
                context = self._generate_task_context(bot_id, task_description)
                tasks.append(
                    self.bots[bot_id].execute_task_with_learning(task_description, context)
                )
            else:
                results[bot_id] = {"status": "error", "message": "Bot not found"}
                
        # Wait for all tasks to complete
        if tasks:
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (bot_id, _) in enumerate(task_assignments.items()):
                if i < len(task_results):
                    if isinstance(task_results[i], Exception):
                        results[bot_id] = {"status": "error", "message": str(task_results[i])}
                    else:
                        results[bot_id] = task_results[i]
                        
        return results
        
    def _generate_task_context(self, bot_id: str, task_description: str) -> str:
        """Generate context for task execution"""
        
        bot = self.bots.get(bot_id)
        if not bot:
            return ""
            
        base_context = f"""SuperInstance Development Context:
- Bot Specialization: {bot.specialization}
- ActiveLog fitness tracking system focus
- Infrastructure: Kubernetes + Docker + PostgreSQL + Redis
- Current Status: Services 70% complete, Domains 40% complete, Infrastructure ready
- Goal: Build cloud server superior to local servers"""

        # Add specialization-specific context
        if bot.specialization == "services":
            base_context += "\n- Priority: Sub-100ms API response times critical for user experience"
            base_context += "\n- Available: Auth service (port 8001), API Gateway (port 8088), PostgreSQL with fitness schema"
            
        elif bot.specialization == "domains":
            base_context += "\n- Priority: User interface development is 60% incomplete - high impact area"
            base_context += "\n- Focus: React components, responsive design, fitness tracking workflows"
            
        elif bot.specialization == "infrastructure":
            base_context += "\n- Priority: Production-ready monitoring and scaling capabilities"
            base_context += "\n- Tools: Kubernetes, Grafana, Prometheus, SSL certificates configured"
            
        elif bot.specialization == "ai":
            base_context += "\n- Priority: Cross-domain analytics engine with intelligent correlations"
            base_context += "\n- Integration: Claude API, vector embeddings, semantic analysis"
            
        return base_context
        
    def get_fleet_stats(self) -> Dict[str, Any]:
        """Get statistics for the entire bot fleet"""
        
        stats = {
            "total_bots": len(self.bots),
            "total_tasks_completed": sum(bot.tasks_completed for bot in self.bots.values()),
            "total_learning_entries": sum(bot.total_learning_entries for bot in self.bots.values()),
            "bot_details": {}
        }
        
        for bot_id, bot in self.bots.items():
            stats["bot_details"][bot_id] = {
                "specialization": bot.specialization,
                "tasks_completed": bot.tasks_completed,
                "learning_entries": bot.total_learning_entries,
                "learning_rate": bot.total_learning_entries / max(bot.tasks_completed, 1)
            }
            
        return stats

# Main integration function for existing system
async def initialize_learning_bots(anthropic_api_key: str) -> BotFleet:
    """Initialize the learning-enabled bot system"""
    
    # Create bot fleet
    fleet = BotFleet(anthropic_api_key)
    
    # Deploy standard bots
    await fleet.deploy_bot_fleet()
    
    # Start learning system
    await fleet.start_learning_system()
    
    return fleet

# Command-line interface for testing
if __name__ == "__main__":
    import sys
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)
        
    async def test_learning_bots():
        print("🤖 Initializing Learning-Enabled Bot System...")
        
        # Initialize fleet
        fleet = await initialize_learning_bots(api_key)
        
        # Test task assignments
        test_tasks = {
            "services-bot-001": "Optimize ActiveLog fitness API endpoints for sub-100ms response times",
            "domains-bot-002": "Implement user dashboard interface with React components",
            "infra-bot-003": "Enhance Kubernetes monitoring with advanced Grafana dashboards", 
            "ai-bot-004": "Create cross-domain analytics engine for health data correlations"
        }
        
        print("\n🚀 Executing tasks with learning enabled...")
        results = await fleet.execute_fleet_tasks(test_tasks)
        
        print("\n📊 Task Execution Results:")
        for bot_id, result in results.items():
            if result["status"] == "success":
                print(f"  ✅ {bot_id}: {result['result']['summary']}")
                print(f"     📝 Learning recorded: {result['learning_recorded']}")
                print(f"     📈 Tasks completed: {result['bot_stats']['tasks_completed']}")
            else:
                print(f"  ❌ {bot_id}: {result.get('message', 'Unknown error')}")
                
        print("\n🧠 Fleet Learning Statistics:")
        stats = fleet.get_fleet_stats()
        print(f"  Total bots: {stats['total_bots']}")
        print(f"  Total tasks: {stats['total_tasks_completed']}")
        print(f"  Learning entries: {stats['total_learning_entries']}")
        
        for bot_id, details in stats["bot_details"].items():
            print(f"  {bot_id}: {details['tasks_completed']} tasks, {details['learning_entries']} learnings")
            
        print("\n🔄 Learning synthesis will run every 15 minutes")
        print("🔍 System audit will run every hour")
        print("✅ Bots are now continuously improving!")
        
        # Wait a bit to let learning system process
        await asyncio.sleep(5)
        
        # Stop learning system for demo
        await fleet.learning_orchestrator.stop_learning_system()
        
    # Run test
    asyncio.run(test_learning_bots())