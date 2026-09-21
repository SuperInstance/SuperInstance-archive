#!/usr/bin/env python3
"""
SuperInstance Bot Learning Engine
Continuous ML system that makes bots more effective through ecosystem-specific learning
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import tiktoken
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BotLearning:
    bot_id: str
    task_completed: str
    ecosystem_insights: List[str]
    code_patterns_learned: List[str]
    system_understanding: Dict[str, str]
    challenges_encountered: List[str]
    optimization_opportunities: List[str]
    timestamp: datetime
    confidence_score: float  # How confident the bot is in these learnings

@dataclass
class TrainingMaterial:
    topic: str
    consolidated_knowledge: str
    source_bots: List[str]
    confidence_level: float
    usage_count: int
    last_updated: datetime
    effectiveness_score: float  # How much this improves bot performance

class BotKnowledgeJournal:
    """Manages individual bot learning journals"""
    
    def __init__(self, journal_dir: str = "/home/activeloguser/activelog/bot-learning-system/journals"):
        self.journal_dir = Path(journal_dir)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def create_learning_entry(self, bot_id: str, task_completed: str, 
                            ecosystem_context: str) -> BotLearning:
        """Create a learning entry from a completed task"""
        
        # Extract insights using intelligent analysis
        insights = self._extract_ecosystem_insights(task_completed, ecosystem_context)
        patterns = self._identify_code_patterns(ecosystem_context)
        understanding = self._assess_system_understanding(ecosystem_context)
        challenges = self._identify_challenges(ecosystem_context)
        optimizations = self._find_optimization_opportunities(ecosystem_context)
        
        return BotLearning(
            bot_id=bot_id,
            task_completed=task_completed,
            ecosystem_insights=insights,
            code_patterns_learned=patterns,
            system_understanding=understanding,
            challenges_encountered=challenges,
            optimization_opportunities=optimizations,
            timestamp=datetime.now(),
            confidence_score=self._calculate_confidence(insights, patterns, understanding)
        )
        
    def save_learning_entry(self, learning: BotLearning):
        """Save learning entry to bot's journal"""
        
        journal_file = self.journal_dir / f"{learning.bot_id}_journal.jsonl"
        
        # Append to journal
        with open(journal_file, 'a') as f:
            json.dump(asdict(learning), f, default=str)
            f.write('\n')
            
        logger.info(f"Saved learning entry for {learning.bot_id}: {len(learning.ecosystem_insights)} insights")
        
    def get_recent_learnings(self, bot_id: str, hours: int = 24) -> List[BotLearning]:
        """Get recent learning entries for a bot"""
        
        journal_file = self.journal_dir / f"{bot_id}_journal.jsonl"
        if not journal_file.exists():
            return []
            
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_learnings = []
        
        with open(journal_file, 'r') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    timestamp = datetime.fromisoformat(data['timestamp'])
                    if timestamp > cutoff_time:
                        learning = BotLearning(**data)
                        recent_learnings.append(learning)
                        
        return recent_learnings
        
    def get_all_bot_learnings(self, hours: int = 24) -> Dict[str, List[BotLearning]]:
        """Get recent learnings from all bots"""
        
        all_learnings = {}
        
        for journal_file in self.journal_dir.glob("*_journal.jsonl"):
            bot_id = journal_file.stem.replace('_journal', '')
            learnings = self.get_recent_learnings(bot_id, hours)
            if learnings:
                all_learnings[bot_id] = learnings
                
        return all_learnings
        
    def _extract_ecosystem_insights(self, task: str, context: str) -> List[str]:
        """Extract insights about the SuperInstance ecosystem"""
        
        insights = []
        combined_text = f"{task} {context}".lower()
        
        # SuperInstance-specific patterns
        superinstance_patterns = {
            "activelog fitness": "ActiveLog is the primary fitness tracking domain with schema-ready database",
            "microservices": "System uses microservices architecture with Kubernetes orchestration",
            "api performance": "Sub-100ms API response times are critical for user experience",
            "redis caching": "Redis caching layer is essential for database load reduction",
            "cross-domain": "Cross-domain analytics is a key differentiator requiring AI integration",
            "user dashboard": "User interface development is 60% incomplete and high priority",
            "grafana monitoring": "Comprehensive monitoring with Grafana dashboards ensures production readiness",
            "claude api": "Claude API integration provides intelligent assistance throughout the system",
            "jwt authentication": "Authentication system uses JWT tokens with role-based access control"
        }
        
        for pattern, insight in superinstance_patterns.items():
            if pattern in combined_text:
                insights.append(insight)
                
        # Add specific learning from context
        if "database" in combined_text:
            insights.append("Database optimization is frequent need - PostgreSQL with vector embeddings")
        if "user experience" in combined_text or "ux" in combined_text:
            insights.append("User experience improvements are high-value tasks for SuperInstance")
        if "performance" in combined_text:
            insights.append("Performance optimization directly impacts SuperInstance superiority claims")
            
        return insights[:5]  # Limit to top 5 insights
        
    def _identify_code_patterns(self, context: str) -> List[str]:
        """Identify reusable code patterns from context"""
        
        patterns = []
        context_lower = context.lower()
        
        # Common SuperInstance patterns
        if "async" in context_lower and "await" in context_lower:
            patterns.append("Async/await pattern used extensively for non-blocking operations")
        if "fastapi" in context_lower:
            patterns.append("FastAPI framework standard for REST API development")
        if "pydantic" in context_lower:
            patterns.append("Pydantic models used for data validation and serialization")
        if "docker" in context_lower or "container" in context_lower:
            patterns.append("Containerization with Docker is standard deployment pattern")
        if "logging" in context_lower:
            patterns.append("Structured logging pattern with timestamp and component identification")
            
        return patterns[:3]  # Limit to top 3 patterns
        
    def _assess_system_understanding(self, context: str) -> Dict[str, str]:
        """Assess understanding of system components"""
        
        understanding = {}
        context_lower = context.lower()
        
        # Component understanding
        if "kubernetes" in context_lower:
            understanding["deployment"] = "Kubernetes orchestration with manifests and services"
        if "redis" in context_lower:
            understanding["caching"] = "Redis used for session management and performance optimization"
        if "postgres" in context_lower:
            understanding["database"] = "PostgreSQL primary database with fitness schema and vector support"
        if "grafana" in context_lower:
            understanding["monitoring"] = "Grafana dashboards provide comprehensive system visibility"
        if "nginx" in context_lower:
            understanding["proxy"] = "Nginx handles load balancing and SSL termination"
            
        return understanding
        
    def _identify_challenges(self, context: str) -> List[str]:
        """Identify challenges encountered"""
        
        challenges = []
        context_lower = context.lower()
        
        # Common challenge indicators
        if "error" in context_lower or "bug" in context_lower:
            challenges.append("Error handling and debugging required attention")
        if "performance" in context_lower and ("slow" in context_lower or "timeout" in context_lower):
            challenges.append("Performance bottlenecks need systematic optimization")
        if "integration" in context_lower and "complex" in context_lower:
            challenges.append("System integration complexity requires careful coordination")
        if "scalability" in context_lower:
            challenges.append("Scalability considerations important for SuperInstance architecture")
            
        return challenges[:3]  # Limit to top 3 challenges
        
    def _find_optimization_opportunities(self, context: str) -> List[str]:
        """Find optimization opportunities"""
        
        opportunities = []
        context_lower = context.lower()
        
        # Optimization patterns
        if "duplicate" in context_lower or "repetitive" in context_lower:
            opportunities.append("Code duplication reduction through better abstraction")
        if "manual" in context_lower and "process" in context_lower:
            opportunities.append("Manual processes can be automated for efficiency")
        if "response time" in context_lower:
            opportunities.append("API response time optimization through caching and query optimization")
        if "resource" in context_lower and ("usage" in context_lower or "consumption" in context_lower):
            opportunities.append("Resource usage optimization for cost and performance benefits")
            
        return opportunities[:3]  # Limit to top 3 opportunities
        
    def _calculate_confidence(self, insights: List[str], patterns: List[str], 
                            understanding: Dict[str, str]) -> float:
        """Calculate confidence score for learnings"""
        
        # Base confidence from amount of learning
        base_confidence = min(0.9, (len(insights) + len(patterns) + len(understanding)) / 10)
        
        # Boost for SuperInstance-specific learnings
        superinstance_keywords = ['activelog', 'superinstance', 'fitness', 'cross-domain']
        relevance_boost = sum(0.1 for keyword in superinstance_keywords 
                            if any(keyword in item.lower() for item in insights))
        
        return min(0.95, base_confidence + relevance_boost)

class TrainingMaterialSynthesizer:
    """Synthesizes bot learnings into improved training materials"""
    
    def __init__(self, training_dir: str = "/home/activeloguser/activelog/bot-learning-system/training"):
        self.training_dir = Path(training_dir)
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.journal = BotKnowledgeJournal()
        
    async def synthesize_learnings(self, anthropic_api_key: str) -> Dict[str, TrainingMaterial]:
        """Synthesize recent bot learnings into training materials"""
        
        # Get all recent learnings
        all_learnings = self.journal.get_all_bot_learnings(hours=4)  # Last 4 hours
        
        if not all_learnings:
            logger.info("No recent learnings to synthesize")
            return {}
            
        # Group learnings by topic
        topic_groups = self._group_learnings_by_topic(all_learnings)
        
        # Synthesize each topic group
        synthesized_materials = {}
        
        async with aiohttp.ClientSession() as session:
            for topic, learnings_group in topic_groups.items():
                try:
                    material = await self._synthesize_topic(
                        session, anthropic_api_key, topic, learnings_group
                    )
                    if material:
                        synthesized_materials[topic] = material
                        self._save_training_material(material)
                        
                except Exception as e:
                    logger.error(f"Failed to synthesize topic {topic}: {e}")
                    
        logger.info(f"Synthesized {len(synthesized_materials)} training materials")
        return synthesized_materials
        
    def _group_learnings_by_topic(self, all_learnings: Dict[str, List[BotLearning]]) -> Dict[str, List[BotLearning]]:
        """Group learnings by topic for synthesis"""
        
        topic_groups = {
            "api_development": [],
            "database_optimization": [],
            "user_interface": [],
            "infrastructure_management": [],
            "ai_integration": [],
            "performance_optimization": [],
            "system_architecture": []
        }
        
        # Topic keywords
        topic_keywords = {
            "api_development": ["api", "endpoint", "rest", "graphql", "service"],
            "database_optimization": ["database", "postgres", "sql", "query", "redis"],
            "user_interface": ["ui", "dashboard", "react", "interface", "user experience"],
            "infrastructure_management": ["kubernetes", "docker", "deployment", "monitoring", "grafana"],
            "ai_integration": ["ai", "claude", "machine learning", "analytics", "intelligence"],
            "performance_optimization": ["performance", "optimization", "caching", "response time"],
            "system_architecture": ["architecture", "microservices", "scalability", "integration"]
        }
        
        # Classify learnings into topics
        for bot_id, learnings in all_learnings.items():
            for learning in learnings:
                classified = False
                
                # Check task and insights for topic keywords
                combined_text = f"{learning.task_completed} {' '.join(learning.ecosystem_insights)}".lower()
                
                for topic, keywords in topic_keywords.items():
                    if any(keyword in combined_text for keyword in keywords):
                        topic_groups[topic].append(learning)
                        classified = True
                        break
                        
                # Default to system_architecture if not classified
                if not classified:
                    topic_groups["system_architecture"].append(learning)
                    
        # Remove empty groups
        return {topic: learnings for topic, learnings in topic_groups.items() if learnings}
        
    async def _synthesize_topic(self, session: aiohttp.ClientSession, api_key: str,
                              topic: str, learnings: List[BotLearning]) -> Optional[TrainingMaterial]:
        """Synthesize learnings for a specific topic using Claude"""
        
        # Prepare synthesis prompt
        learnings_summary = self._prepare_learnings_summary(learnings)
        
        synthesis_prompt = f"""You are the SuperInstance Training Bot. Synthesize the following bot learnings into improved training material for {topic.replace('_', ' ')}.

RECENT BOT LEARNINGS ({len(learnings)} entries):
{learnings_summary}

SYNTHESIS REQUIREMENTS:
1. Create consolidated knowledge that makes future bots more effective
2. Identify the most valuable patterns and insights
3. Focus on SuperInstance-specific best practices
4. Include actionable guidance for similar tasks
5. Remove redundant or low-value information

Create training material that will make bots 20% more effective at {topic.replace('_', ' ')} tasks.

TRAINING MATERIAL:"""

        try:
            # Call Claude for synthesis
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-sonnet-20240229",
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": synthesis_prompt}]
                }
            ) as response:
                
                if response.status != 200:
                    logger.error(f"Claude API error: {response.status}")
                    return None
                    
                result = await response.json()
                synthesized_content = result["content"][0]["text"]
                
                # Calculate effectiveness metrics
                source_bots = list(set(learning.bot_id for learning in learnings))
                avg_confidence = sum(learning.confidence_score for learning in learnings) / len(learnings)
                
                return TrainingMaterial(
                    topic=topic,
                    consolidated_knowledge=synthesized_content,
                    source_bots=source_bots,
                    confidence_level=avg_confidence,
                    usage_count=0,
                    last_updated=datetime.now(),
                    effectiveness_score=0.0  # Will be updated based on usage
                )
                
        except Exception as e:
            logger.error(f"Failed to synthesize topic {topic}: {e}")
            return None
            
    def _prepare_learnings_summary(self, learnings: List[BotLearning]) -> str:
        """Prepare a summary of learnings for synthesis"""
        
        summary_parts = []
        
        for i, learning in enumerate(learnings):
            summary_parts.append(f"""
BOT {learning.bot_id} - Task: {learning.task_completed}
Insights: {'; '.join(learning.ecosystem_insights[:3])}
Patterns: {'; '.join(learning.code_patterns_learned)}
Understanding: {'; '.join(f'{k}: {v}' for k, v in learning.system_understanding.items())}
Challenges: {'; '.join(learning.challenges_encountered)}
Optimizations: {'; '.join(learning.optimization_opportunities)}
Confidence: {learning.confidence_score:.1%}
""")
            
        return '\n'.join(summary_parts)
        
    def _save_training_material(self, material: TrainingMaterial):
        """Save training material to file"""
        
        filename = f"{material.topic}_training.json"
        filepath = self.training_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(material), f, indent=2, default=str)
            
        logger.info(f"Saved training material: {material.topic}")

class SystemAuditor:
    """Audits system effectiveness and cleans up obsolete materials"""
    
    def __init__(self, learning_system_dir: str = "/home/activeloguser/activelog/bot-learning-system"):
        self.learning_dir = Path(learning_system_dir)
        self.journal = BotKnowledgeJournal()
        self.synthesizer = TrainingMaterialSynthesizer()
        
    async def audit_and_cleanup(self) -> Dict[str, Any]:
        """Perform system audit and cleanup obsolete materials"""
        
        audit_results = {
            "journals_audited": 0,
            "obsolete_entries_removed": 0,
            "training_materials_updated": 0,
            "effectiveness_improvements": {}
        }
        
        # Audit training material effectiveness
        training_files = list((self.learning_dir / "training").glob("*.json"))
        
        for training_file in training_files:
            try:
                with open(training_file, 'r') as f:
                    material_data = json.load(f)
                    
                material = TrainingMaterial(**material_data)
                
                # Check if material is still effective
                is_effective = await self._assess_material_effectiveness(material)
                
                if is_effective:
                    # Update usage metrics
                    material.usage_count += 1
                    material.effectiveness_score = min(1.0, material.effectiveness_score + 0.1)
                    
                    # Save updated material
                    with open(training_file, 'w') as f:
                        json.dump(asdict(material), f, indent=2, default=str)
                        
                    audit_results["training_materials_updated"] += 1
                    
                else:
                    # Remove ineffective material
                    training_file.unlink()
                    logger.info(f"Removed ineffective training material: {material.topic}")
                    
            except Exception as e:
                logger.error(f"Error auditing {training_file}: {e}")
                
        # Clean up old journal entries
        cleanup_results = await self._cleanup_old_journals()
        audit_results.update(cleanup_results)
        
        logger.info(f"System audit complete: {audit_results}")
        return audit_results
        
    async def _assess_material_effectiveness(self, material: TrainingMaterial) -> bool:
        """Assess if training material is still effective"""
        
        # Check age - materials older than 7 days need validation
        age_days = (datetime.now() - material.last_updated).days
        
        if age_days < 3:
            return True  # Recent materials are assumed effective
            
        # Check usage - unused materials for > 7 days are candidates for removal
        if age_days > 7 and material.usage_count == 0:
            return False
            
        # Check relevance - low confidence materials that haven't been used
        if material.confidence_level < 0.5 and material.usage_count < 2:
            return False
            
        return True  # Keep by default
        
    async def _cleanup_old_journals(self) -> Dict[str, int]:
        """Clean up old journal entries"""
        
        cleanup_results = {
            "journals_audited": 0,
            "obsolete_entries_removed": 0
        }
        
        # Clean journals older than 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        
        for journal_file in (self.learning_dir / "journals").glob("*_journal.jsonl"):
            try:
                lines_to_keep = []
                removed_count = 0
                
                with open(journal_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            timestamp = datetime.fromisoformat(data['timestamp'])
                            
                            if timestamp > cutoff_date:
                                lines_to_keep.append(line)
                            else:
                                removed_count += 1
                                
                # Rewrite journal with only recent entries
                if removed_count > 0:
                    with open(journal_file, 'w') as f:
                        f.writelines(lines_to_keep)
                        
                cleanup_results["journals_audited"] += 1
                cleanup_results["obsolete_entries_removed"] += removed_count
                
                logger.info(f"Cleaned {journal_file.stem}: removed {removed_count} old entries")
                
            except Exception as e:
                logger.error(f"Error cleaning journal {journal_file}: {e}")
                
        return cleanup_results

class BotLearningOrchestrator:
    """Main orchestrator for the bot learning system"""
    
    def __init__(self, anthropic_api_key: str):
        self.api_key = anthropic_api_key
        self.journal = BotKnowledgeJournal()
        self.synthesizer = TrainingMaterialSynthesizer()
        self.auditor = SystemAuditor()
        self.running = False
        
    async def start_learning_system(self):
        """Start the continuous learning system"""
        
        self.running = True
        logger.info("Bot learning system started")
        
        # Start background tasks
        synthesis_task = asyncio.create_task(self._synthesis_loop())
        audit_task = asyncio.create_task(self._audit_loop())
        
        # Wait for completion
        await asyncio.gather(synthesis_task, audit_task)
        
    async def stop_learning_system(self):
        """Stop the learning system"""
        
        self.running = False
        logger.info("Bot learning system stopped")
        
    async def _synthesis_loop(self):
        """Run synthesis every 15 minutes"""
        
        while self.running:
            try:
                logger.info("Starting learning synthesis cycle")
                
                # Synthesize recent learnings
                materials = await self.synthesizer.synthesize_learnings(self.api_key)
                
                if materials:
                    logger.info(f"Synthesized {len(materials)} training materials")
                    
                    # Log synthesis to micro_updates
                    await self._log_synthesis_activity(len(materials))
                    
                # Wait 15 minutes
                await asyncio.sleep(900)  # 15 minutes
                
            except Exception as e:
                logger.error(f"Synthesis loop error: {e}")
                await asyncio.sleep(300)  # 5 minutes on error
                
    async def _audit_loop(self):
        """Run system audit every hour"""
        
        while self.running:
            try:
                logger.info("Starting system audit cycle")
                
                # Perform audit and cleanup
                audit_results = await self.auditor.audit_and_cleanup()
                
                logger.info(f"Audit complete: {audit_results}")
                
                # Log audit to micro_updates
                await self._log_audit_activity(audit_results)
                
                # Wait 1 hour
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Audit loop error: {e}")
                await asyncio.sleep(1800)  # 30 minutes on error
                
    async def _log_synthesis_activity(self, materials_count: int):
        """Log synthesis activity to micro_updates.log"""
        
        try:
            timestamp = datetime.now().strftime('%H:%M')
            log_entry = f"{timestamp}|training-bot|COMPLETE|synthesized-{materials_count}-training-materials-from-bot-learnings\n"
            
            with open('/home/activeloguser/activelog/micro_updates.log', 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log synthesis activity: {e}")
            
    async def _log_audit_activity(self, audit_results: Dict[str, Any]):
        """Log audit activity to micro_updates.log"""
        
        try:
            timestamp = datetime.now().strftime('%H:%M')
            removed = audit_results["obsolete_entries_removed"]
            updated = audit_results["training_materials_updated"]
            
            log_entry = f"{timestamp}|audit-bot|COMPLETE|cleaned-{removed}-obsolete-entries-updated-{updated}-training-materials\n"
            
            with open('/home/activeloguser/activelog/micro_updates.log', 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log audit activity: {e}")
            
    def record_bot_learning(self, bot_id: str, task_completed: str, 
                          ecosystem_context: str) -> str:
        """Record a learning entry for a bot"""
        
        learning = self.journal.create_learning_entry(bot_id, task_completed, ecosystem_context)
        self.journal.save_learning_entry(learning)
        
        return f"Learning recorded: {len(learning.ecosystem_insights)} insights, {learning.confidence_score:.1%} confidence"

# Integration function for existing bots
def create_bot_learning_hook():
    """Create a function that can be called by existing bots to record learnings"""
    
    def record_learning(bot_id: str, task_completed: str, context: str = ""):
        """Function to be called by bots after task completion"""
        
        try:
            # Initialize learning system (lightweight)
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not set - learning disabled")
                return
                
            journal = BotKnowledgeJournal()
            learning = journal.create_learning_entry(bot_id, task_completed, context)
            journal.save_learning_entry(learning)
            
            logger.info(f"Recorded learning for {bot_id}: {len(learning.ecosystem_insights)} insights")
            
        except Exception as e:
            logger.error(f"Failed to record learning for {bot_id}: {e}")
            
    return record_learning

# Example usage
if __name__ == "__main__":
    import sys
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)
        
    async def test_learning_system():
        # Initialize learning orchestrator
        orchestrator = BotLearningOrchestrator(api_key)
        
        # Test learning recording
        test_learnings = [
            ("services-bot-001", "Optimized ActiveLog fitness API response times", 
             "Implemented Redis caching and database query optimization, achieved 85ms average response time"),
            ("domains-bot-002", "Created user dashboard interface components", 
             "Built React components with responsive design, integrated with fitness API, improved user experience"),
            ("infra-bot-003", "Enhanced Kubernetes monitoring dashboards", 
             "Configured Grafana with custom metrics, added alerting rules, improved system visibility")
        ]
        
        print("🧠 Testing Bot Learning System...")
        
        for bot_id, task, context in test_learnings:
            result = orchestrator.record_bot_learning(bot_id, task, context)
            print(f"  📝 {bot_id}: {result}")
            
        print("\n🔄 Running synthesis cycle...")
        materials = await orchestrator.synthesizer.synthesize_learnings(api_key)
        
        print(f"✅ Synthesized {len(materials)} training materials:")
        for topic, material in materials.items():
            print(f"  📚 {topic}: {len(material.consolidated_knowledge)} chars, {material.confidence_level:.1%} confidence")
            
        print("\n🔍 Running system audit...")
        audit_results = await orchestrator.auditor.audit_and_cleanup()
        print(f"📊 Audit results: {audit_results}")
        
    # Run test
    asyncio.run(test_learning_system())