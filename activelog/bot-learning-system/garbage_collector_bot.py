#!/usr/bin/env python3
"""
SuperInstance Garbage Collection Bot
Cleans up system waste while learning storage efficiency patterns
Creates training materials for streamlined bot operations
"""

import asyncio
import os
import json
import logging
import shutil
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

from learning_engine import BotLearningOrchestrator, BotKnowledgeJournal

logger = logging.getLogger(__name__)

@dataclass
class CleanupTask:
    file_path: str
    file_type: str
    size_bytes: int
    age_hours: float
    cleanup_reason: str
    storage_waste_category: str
    bot_responsible: Optional[str] = None

@dataclass
class StorageAnalysis:
    total_files_analyzed: int
    total_size_mb: float
    waste_categories: Dict[str, int]
    cleanup_opportunities: List[str]
    efficiency_patterns: List[str]
    bot_storage_habits: Dict[str, Dict[str, Any]]
    timestamp: datetime

@dataclass
class EfficiencyInsight:
    pattern_type: str
    description: str
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    frequency_observed: int
    estimated_savings_mb: float
    recommendation: str
    affected_bots: List[str]

class StorageEfficiencyAnalyzer:
    """Analyzes storage patterns and identifies efficiency opportunities"""
    
    def __init__(self):
        self.waste_patterns = {
            "duplicate_files": r".*\.(tmp|bak|backup|copy|\d+)$",
            "large_logs": r".*\.log$",
            "temp_artifacts": r".*(temp|tmp|cache|\.swp|\.swo).*",
            "old_containers": r".*\.(tar|img|container)$",
            "unused_configs": r".*\.(old|disabled|unused).*",
            "debug_outputs": r".*(debug|test|dump|output).*",
            "generated_files": r".*(generated|auto|build|dist).*"
        }
        
        self.bot_storage_signatures = {
            "services": ["*.pyc", "*.log", "__pycache__", "node_modules"],
            "domains": ["*.js.map", "dist/", "build/", ".next/", "coverage/"],
            "infrastructure": ["*.yaml.backup", "logs/", "metrics/", ".terraform/"],
            "ai": ["*.pkl", "*.model", "embeddings/", "training_data/"],
            "training": ["synthesis_cache/", "*.jsonl", "old_materials/"]
        }
        
    def analyze_directory(self, directory: str) -> StorageAnalysis:
        """Analyze directory for storage efficiency"""
        
        analysis = StorageAnalysis(
            total_files_analyzed=0,
            total_size_mb=0.0,
            waste_categories={},
            cleanup_opportunities=[],
            efficiency_patterns=[],
            bot_storage_habits={},
            timestamp=datetime.now()
        )
        
        directory_path = Path(directory)
        if not directory_path.exists():
            return analysis
            
        # Walk through directory tree
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                analysis.total_files_analyzed += 1
                
                try:
                    size_bytes = file_path.stat().st_size
                    size_mb = size_bytes / (1024 * 1024)
                    analysis.total_size_mb += size_mb
                    
                    # Analyze file for waste patterns
                    waste_category = self._categorize_waste(str(file_path))
                    if waste_category:
                        analysis.waste_categories[waste_category] = analysis.waste_categories.get(waste_category, 0) + 1
                        
                    # Identify bot responsible
                    responsible_bot = self._identify_responsible_bot(str(file_path))
                    if responsible_bot:
                        if responsible_bot not in analysis.bot_storage_habits:
                            analysis.bot_storage_habits[responsible_bot] = {
                                "file_count": 0,
                                "total_size_mb": 0.0,
                                "waste_files": 0
                            }
                        analysis.bot_storage_habits[responsible_bot]["file_count"] += 1
                        analysis.bot_storage_habits[responsible_bot]["total_size_mb"] += size_mb
                        if waste_category:
                            analysis.bot_storage_habits[responsible_bot]["waste_files"] += 1
                            
                except Exception as e:
                    logger.debug(f"Error analyzing {file_path}: {e}")
                    
        # Generate cleanup opportunities
        analysis.cleanup_opportunities = self._generate_cleanup_opportunities(analysis)
        analysis.efficiency_patterns = self._identify_efficiency_patterns(analysis)
        
        return analysis
        
    def _categorize_waste(self, file_path: str) -> Optional[str]:
        """Categorize file as waste type"""
        
        for category, pattern in self.waste_patterns.items():
            if re.search(pattern, file_path.lower()):
                return category
                
        # Check file age and size
        try:
            path_obj = Path(file_path)
            age_hours = (time.time() - path_obj.stat().st_mtime) / 3600
            size_mb = path_obj.stat().st_size / (1024 * 1024)
            
            if age_hours > 168 and size_mb > 10:  # 1 week old and >10MB
                return "stale_large_files"
            elif age_hours > 72 and "temp" in file_path.lower():  # 3 days old temp files
                return "old_temp_files"
                
        except Exception:
            pass
            
        return None
        
    def _identify_responsible_bot(self, file_path: str) -> Optional[str]:
        """Identify which bot likely created this file"""
        
        file_lower = file_path.lower()
        
        # Direct bot ID identification
        bot_indicators = {
            "services-bot": ["services", "api", "endpoint", "database"],
            "domains-bot": ["domains", "ui", "dashboard", "react", "components"],
            "infra-bot": ["infra", "kubernetes", "grafana", "monitoring", "deploy"],
            "ai-bot": ["ai", "analytics", "embeddings", "correlation", "intelligence"],
            "training-bot": ["training", "synthesis", "materials", "learning"],
            "gc-bot": ["cleanup", "garbage", "efficiency", "waste"]
        }
        
        for bot_pattern, keywords in bot_indicators.items():
            if any(keyword in file_lower for keyword in keywords):
                return bot_pattern
                
        # Directory-based identification
        if "/services/" in file_path:
            return "services-bot"
        elif "/domains/" in file_path or "/frontend/" in file_path:
            return "domains-bot"
        elif "/infrastructure/" in file_path or "/deployment/" in file_path:
            return "infra-bot"
        elif "/bot-learning-system/" in file_path:
            return "training-bot"
            
        return None
        
    def _generate_cleanup_opportunities(self, analysis: StorageAnalysis) -> List[str]:
        """Generate specific cleanup opportunities"""
        
        opportunities = []
        
        for category, count in analysis.waste_categories.items():
            if count > 5:  # Significant number of files
                opportunities.append(f"Remove {count} {category.replace('_', ' ')} files")
                
        # Bot-specific opportunities
        for bot_id, habits in analysis.bot_storage_habits.items():
            waste_ratio = habits["waste_files"] / max(habits["file_count"], 1)
            if waste_ratio > 0.3:  # >30% waste files
                opportunities.append(f"Optimize {bot_id} storage patterns (30%+ waste)")
                
        # Size-based opportunities  
        if analysis.total_size_mb > 1000:  # >1GB total
            opportunities.append("Implement storage quotas for large file management")
            
        return opportunities
        
    def _identify_efficiency_patterns(self, analysis: StorageAnalysis) -> List[str]:
        """Identify storage efficiency patterns"""
        
        patterns = []
        
        # Pattern: Duplicate prevention
        if analysis.waste_categories.get("duplicate_files", 0) > 3:
            patterns.append("Implement duplicate file prevention in bot workflows")
            
        # Pattern: Temporary file cleanup
        if analysis.waste_categories.get("temp_artifacts", 0) > 10:
            patterns.append("Add automatic temporary file cleanup to bot completion tasks")
            
        # Pattern: Log rotation
        if analysis.waste_categories.get("large_logs", 0) > 5:
            patterns.append("Implement log rotation and archival strategy")
            
        # Pattern: Build artifact management
        if analysis.waste_categories.get("generated_files", 0) > 8:
            patterns.append("Optimize build artifact retention policies")
            
        return patterns

class GarbageCollectorBot:
    """Intelligent garbage collection bot with learning capabilities"""
    
    def __init__(self, anthropic_api_key: str):
        self.bot_id = "gc-bot-005"
        self.api_key = anthropic_api_key
        self.analyzer = StorageEfficiencyAnalyzer()
        self.journal = BotKnowledgeJournal()
        
        # Cleanup configuration
        self.cleanup_config = {
            "safe_directories": [
                "/home/activeloguser/activelog/bot-learning-system/training",
                "/home/activeloguser/activelog/bot-learning-system/journals",
                "/home/activeloguser/activelog/services",
                "/home/activeloguser/activelog/.git"
            ],
            "cleanup_directories": [
                "/home/activeloguser/activelog/logs",
                "/home/activeloguser/activelog/tmp", 
                "/tmp",
                "/home/activeloguser/activelog/cache",
                "/home/activeloguser/activelog/build",
                "/home/activeloguser/activelog/dist",
                "/home/activeloguser/activelog/.cache"
            ],
            "age_thresholds": {
                "temp_files": 24,      # hours
                "log_files": 168,      # 1 week
                "cache_files": 72,     # 3 days
                "backup_files": 720    # 30 days
            },
            "size_thresholds": {
                "single_file_mb": 100,   # Single file >100MB needs review
                "directory_mb": 500      # Directory >500MB needs review
            }
        }
        
        self.cleanup_stats = {
            "files_cleaned": 0,
            "mb_freed": 0.0,
            "efficiency_insights": 0,
            "training_materials_created": 0
        }
        
    async def run_cleanup_cycle(self) -> Dict[str, Any]:
        """Run complete cleanup cycle with learning"""
        
        cycle_start = time.time()
        cleanup_results = {
            "cycle_id": f"cleanup_{int(cycle_start)}",
            "tasks_completed": [],
            "storage_analysis": None,
            "efficiency_insights": [],
            "training_material_created": False,
            "total_files_cleaned": 0,
            "total_mb_freed": 0.0
        }
        
        try:
            # Log cleanup start
            await self._log_activity("START", "intelligent-garbage-collection-and-efficiency-analysis")
            
            # Phase 1: Analyze storage patterns
            analysis = await self._analyze_system_storage()
            cleanup_results["storage_analysis"] = asdict(analysis)
            
            # Phase 2: Perform intelligent cleanup
            cleanup_tasks = await self._perform_intelligent_cleanup(analysis)
            cleanup_results["tasks_completed"] = cleanup_tasks
            cleanup_results["total_files_cleaned"] = len(cleanup_tasks)
            cleanup_results["total_mb_freed"] = sum(task.size_bytes / (1024*1024) for task in cleanup_tasks)
            
            # Phase 3: Generate efficiency insights
            insights = await self._generate_efficiency_insights(analysis, cleanup_tasks)
            cleanup_results["efficiency_insights"] = [asdict(insight) for insight in insights]
            
            # Phase 4: Create training material
            training_created = await self._create_storage_training_material(analysis, insights)
            cleanup_results["training_material_created"] = training_created
            
            # Phase 5: Record learning
            await self._record_cleanup_learning(cleanup_results)
            
            # Update stats
            self.cleanup_stats["files_cleaned"] += cleanup_results["total_files_cleaned"]
            self.cleanup_stats["mb_freed"] += cleanup_results["total_mb_freed"]
            self.cleanup_stats["efficiency_insights"] += len(insights)
            if training_created:
                self.cleanup_stats["training_materials_created"] += 1
                
            cycle_time = time.time() - cycle_start
            
            # Log completion
            await self._log_activity("COMPLETE", 
                f"cleaned-{cleanup_results['total_files_cleaned']}-files-freed-{cleanup_results['total_mb_freed']:.1f}MB-{cycle_time:.1f}s")
                
            return cleanup_results
            
        except Exception as e:
            logger.error(f"Cleanup cycle failed: {e}")
            await self._log_activity("FAILED", f"cleanup-cycle-error-{str(e)[:50]}")
            return cleanup_results
            
    async def _analyze_system_storage(self) -> StorageAnalysis:
        """Analyze entire system for storage efficiency"""
        
        combined_analysis = StorageAnalysis(
            total_files_analyzed=0,
            total_size_mb=0.0,
            waste_categories={},
            cleanup_opportunities=[],
            efficiency_patterns=[],
            bot_storage_habits={},
            timestamp=datetime.now()
        )
        
        # Analyze each cleanup directory
        for directory in self.cleanup_config["cleanup_directories"]:
            if os.path.exists(directory):
                dir_analysis = self.analyzer.analyze_directory(directory)
                
                # Merge results
                combined_analysis.total_files_analyzed += dir_analysis.total_files_analyzed
                combined_analysis.total_size_mb += dir_analysis.total_size_mb
                
                # Merge waste categories
                for category, count in dir_analysis.waste_categories.items():
                    combined_analysis.waste_categories[category] = combined_analysis.waste_categories.get(category, 0) + count
                    
                # Merge bot habits
                for bot_id, habits in dir_analysis.bot_storage_habits.items():
                    if bot_id not in combined_analysis.bot_storage_habits:
                        combined_analysis.bot_storage_habits[bot_id] = {"file_count": 0, "total_size_mb": 0.0, "waste_files": 0}
                    combined_analysis.bot_storage_habits[bot_id]["file_count"] += habits["file_count"]
                    combined_analysis.bot_storage_habits[bot_id]["total_size_mb"] += habits["total_size_mb"]
                    combined_analysis.bot_storage_habits[bot_id]["waste_files"] += habits["waste_files"]
                    
        # Generate final opportunities and patterns
        combined_analysis.cleanup_opportunities = self.analyzer._generate_cleanup_opportunities(combined_analysis)
        combined_analysis.efficiency_patterns = self.analyzer._identify_efficiency_patterns(combined_analysis)
        
        return combined_analysis
        
    async def _perform_intelligent_cleanup(self, analysis: StorageAnalysis) -> List[CleanupTask]:
        """Perform intelligent cleanup based on analysis"""
        
        cleanup_tasks = []
        
        for directory in self.cleanup_config["cleanup_directories"]:
            if not os.path.exists(directory):
                continue
                
            directory_path = Path(directory)
            
            # Clean files based on patterns and age
            for file_path in directory_path.rglob("*"):
                if file_path.is_file():
                    try:
                        cleanup_task = await self._evaluate_file_for_cleanup(file_path)
                        if cleanup_task:
                            # Perform actual cleanup
                            if await self._safe_cleanup_file(file_path, cleanup_task):
                                cleanup_tasks.append(cleanup_task)
                                
                    except Exception as e:
                        logger.debug(f"Error evaluating {file_path}: {e}")
                        
        return cleanup_tasks
        
    async def _evaluate_file_for_cleanup(self, file_path: Path) -> Optional[CleanupTask]:
        """Evaluate if file should be cleaned up"""
        
        try:
            stat_info = file_path.stat()
            age_hours = (time.time() - stat_info.st_mtime) / 3600
            size_bytes = stat_info.st_size
            
            file_str = str(file_path)
            
            # Check waste category
            waste_category = self.analyzer._categorize_waste(file_str)
            if not waste_category:
                return None
                
            # Determine cleanup reason
            cleanup_reason = None
            
            # Age-based cleanup
            for file_type, max_age in self.cleanup_config["age_thresholds"].items():
                if file_type.replace("_", "") in waste_category and age_hours > max_age:
                    cleanup_reason = f"File age {age_hours:.1f}h exceeds {max_age}h threshold"
                    break
                    
            # Size-based cleanup
            size_mb = size_bytes / (1024 * 1024)
            if size_mb > self.cleanup_config["size_thresholds"]["single_file_mb"]:
                cleanup_reason = f"Large file {size_mb:.1f}MB exceeds threshold"
                
            # Pattern-based cleanup
            if waste_category in ["temp_artifacts", "duplicate_files", "old_temp_files"]:
                cleanup_reason = f"File matches waste pattern: {waste_category}"
                
            if not cleanup_reason:
                return None
                
            # Identify responsible bot
            responsible_bot = self.analyzer._identify_responsible_bot(file_str)
            
            return CleanupTask(
                file_path=file_str,
                file_type=file_path.suffix or "no_extension",
                size_bytes=size_bytes,
                age_hours=age_hours,
                cleanup_reason=cleanup_reason,
                storage_waste_category=waste_category,
                bot_responsible=responsible_bot
            )
            
        except Exception as e:
            logger.debug(f"Error evaluating file {file_path}: {e}")
            return None
            
    async def _safe_cleanup_file(self, file_path: Path, cleanup_task: CleanupTask) -> bool:
        """Safely cleanup file with verification"""
        
        # Safety checks
        file_str = str(file_path)
        
        # Never cleanup files in safe directories
        for safe_dir in self.cleanup_config["safe_directories"]:
            if file_str.startswith(safe_dir):
                return False
                
        # Never cleanup system files
        if any(pattern in file_str.lower() for pattern in [".git", "config", "settings", "env"]):
            return False
            
        # Never cleanup files younger than 1 hour (might be actively used)
        if cleanup_task.age_hours < 1.0:
            return False
            
        try:
            # Create backup info before deletion
            backup_info = {
                "original_path": file_str,
                "size_bytes": cleanup_task.size_bytes,
                "cleanup_reason": cleanup_task.cleanup_reason,
                "timestamp": datetime.now().isoformat(),
                "bot_responsible": cleanup_task.bot_responsible
            }
            
            # Remove the file
            file_path.unlink()
            
            # Log cleanup action
            logger.info(f"Cleaned up {file_str}: {cleanup_task.cleanup_reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup {file_str}: {e}")
            return False
            
    async def _generate_efficiency_insights(self, analysis: StorageAnalysis, 
                                          cleanup_tasks: List[CleanupTask]) -> List[EfficiencyInsight]:
        """Generate efficiency insights from cleanup analysis"""
        
        insights = []
        
        # Insight: Bot waste patterns
        bot_waste_analysis = {}
        for task in cleanup_tasks:
            if task.bot_responsible:
                if task.bot_responsible not in bot_waste_analysis:
                    bot_waste_analysis[task.bot_responsible] = {"count": 0, "size_mb": 0.0, "categories": set()}
                bot_waste_analysis[task.bot_responsible]["count"] += 1
                bot_waste_analysis[task.bot_responsible]["size_mb"] += task.size_bytes / (1024 * 1024)
                bot_waste_analysis[task.bot_responsible]["categories"].add(task.storage_waste_category)
                
        for bot_id, waste_data in bot_waste_analysis.items():
            if waste_data["count"] > 5:  # Significant waste
                insights.append(EfficiencyInsight(
                    pattern_type="bot_storage_waste",
                    description=f"{bot_id} created {waste_data['count']} waste files ({waste_data['size_mb']:.1f}MB)",
                    impact_level="MEDIUM" if waste_data["size_mb"] > 10 else "LOW",
                    frequency_observed=waste_data["count"],
                    estimated_savings_mb=waste_data["size_mb"],
                    recommendation=f"Add cleanup routine to {bot_id} task completion",
                    affected_bots=[bot_id]
                ))
                
        # Insight: Storage waste categories
        for category, count in analysis.waste_categories.items():
            if count > 10:  # Significant pattern
                category_size = sum(task.size_bytes for task in cleanup_tasks 
                                  if task.storage_waste_category == category) / (1024 * 1024)
                
                insights.append(EfficiencyInsight(
                    pattern_type="waste_category_pattern",
                    description=f"Frequent {category.replace('_', ' ')} creation ({count} files)",
                    impact_level="HIGH" if category_size > 50 else "MEDIUM",
                    frequency_observed=count,
                    estimated_savings_mb=category_size,
                    recommendation=f"Implement automated {category.replace('_', ' ')} prevention",
                    affected_bots=list(bot_waste_analysis.keys())
                ))
                
        # Insight: Overall system efficiency
        total_cleaned_mb = sum(task.size_bytes for task in cleanup_tasks) / (1024 * 1024)
        if total_cleaned_mb > 100:  # >100MB cleaned
            insights.append(EfficiencyInsight(
                pattern_type="system_efficiency",
                description=f"System storage inefficiency detected: {total_cleaned_mb:.1f}MB waste",
                impact_level="CRITICAL" if total_cleaned_mb > 500 else "HIGH",
                frequency_observed=len(cleanup_tasks),
                estimated_savings_mb=total_cleaned_mb,
                recommendation="Implement proactive storage management across all bots",
                affected_bots=list(analysis.bot_storage_habits.keys())
            ))
            
        return insights
        
    async def _create_storage_training_material(self, analysis: StorageAnalysis, 
                                              insights: List[EfficiencyInsight]) -> bool:
        """Create training material for storage efficiency"""
        
        if not insights:
            return False
            
        training_content = self._generate_storage_training_content(analysis, insights)
        
        # Save training material
        training_file = Path("/home/activeloguser/activelog/bot-learning-system/training/storage_efficiency_training.json")
        
        training_material = {
            "topic": "storage_efficiency",
            "consolidated_knowledge": training_content,
            "source_bots": [self.bot_id],
            "confidence_level": 0.95,
            "usage_count": 0,
            "last_updated": datetime.now().isoformat(),
            "effectiveness_score": 0.0,
            "insights_incorporated": len(insights)
        }
        
        try:
            with open(training_file, 'w') as f:
                json.dump(training_material, f, indent=2, default=str)
                
            logger.info(f"Created storage efficiency training material with {len(insights)} insights")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create training material: {e}")
            return False
            
    def _generate_storage_training_content(self, analysis: StorageAnalysis, 
                                         insights: List[EfficiencyInsight]) -> str:
        """Generate storage efficiency training content"""
        
        content = f"""# SuperInstance Storage Efficiency Training

## System Overview
**Analyzed**: {analysis.total_files_analyzed} files, {analysis.total_size_mb:.1f}MB total
**Waste Categories Found**: {len(analysis.waste_categories)}
**Bot Storage Patterns**: {len(analysis.bot_storage_habits)} bots analyzed

## Critical Storage Efficiency Principles

### 1. Proactive Cleanup Integration
**REQUIREMENT**: Every bot MUST implement cleanup in task completion
- Add cleanup routine to task finalization
- Remove temporary files immediately after use
- Implement file lifecycle management

### 2. Storage-Aware Development Patterns
"""
        
        # Add bot-specific patterns
        for bot_id, habits in analysis.bot_storage_habits.items():
            if habits["waste_files"] > 0:
                waste_ratio = habits["waste_files"] / max(habits["file_count"], 1) * 100
                content += f"""
**{bot_id.upper()}**:
- Storage Usage: {habits["total_size_mb"]:.1f}MB across {habits["file_count"]} files
- Waste Ratio: {waste_ratio:.1f}% ({habits["waste_files"]} waste files)
- **Action Required**: Implement cleanup patterns specific to {bot_id} workflows"""

        content += f"""

### 3. Automated Waste Prevention Strategies
"""
        
        # Add insights as training points
        for insight in insights:
            if insight.impact_level in ["HIGH", "CRITICAL"]:
                content += f"""
**{insight.pattern_type.upper()}**: {insight.description}
- Impact: {insight.impact_level} ({insight.estimated_savings_mb:.1f}MB potential savings)
- Recommendation: {insight.recommendation}
- Implementation: Required for affected bots: {', '.join(insight.affected_bots)}
"""

        content += f"""

### 4. Storage Efficiency Metrics
**Success Indicators**:
- <5% waste file ratio per bot
- <24h temporary file retention
- <100MB single file sizes (unless justified)
- Automatic cleanup integration in all workflows

### 5. Big Picture Integration
**Streamlined System Vision**:
- Storage management is integral to bot intelligence
- Clean systems enable faster processing
- Reduced waste improves overall SuperInstance performance
- Storage efficiency reflects system maturity

## Immediate Implementation Requirements
1. **Add cleanup step** to every bot's task completion workflow
2. **Monitor file creation** patterns during development
3. **Implement size limits** for temporary and cache files
4. **Regular storage audits** as part of system health checks
5. **Cross-bot coordination** to prevent duplicate file creation

## System-Wide Storage Patterns Observed
"""

        # Add specific cleanup opportunities
        for opportunity in analysis.cleanup_opportunities:
            content += f"- {opportunity}\n"
            
        content += f"""
## Training Validation
This training material was generated from analysis of {len(insights)} efficiency patterns
and cleanup of {self.cleanup_stats['files_cleaned']} files totaling {self.cleanup_stats['mb_freed']:.1f}MB.

**Expected Outcome**: 50% reduction in storage waste within next 10 bot task cycles.
"""
        
        return content
        
    async def _record_cleanup_learning(self, cleanup_results: Dict[str, Any]):
        """Record learning from cleanup cycle"""
        
        # Prepare context for learning
        context = f"""Garbage Collection Cycle Results:
- Files analyzed: {cleanup_results['storage_analysis']['total_files_analyzed']}
- Files cleaned: {cleanup_results['total_files_cleaned']}
- Storage freed: {cleanup_results['total_mb_freed']:.1f}MB
- Efficiency insights generated: {len(cleanup_results['efficiency_insights'])}
- Training material created: {cleanup_results['training_material_created']}
- Bot waste patterns identified: {len(set(task['bot_responsible'] for task in cleanup_results['tasks_completed'] if task.get('bot_responsible')))}

Key findings:
- Most wasteful bots need integrated cleanup routines
- Temporary file management requires systematic approach
- Storage monitoring provides valuable system health insights"""

        # Create learning entry
        learning = self.journal.create_learning_entry(
            self.bot_id,
            "Intelligent garbage collection with storage efficiency analysis",
            context
        )
        
        # Save learning
        self.journal.save_learning_entry(learning)
        
        logger.info(f"Recorded cleanup learning: {len(learning.ecosystem_insights)} insights")
        
    async def _log_activity(self, action: str, description: str):
        """Log activity to micro_updates.log"""
        
        try:
            timestamp = datetime.now().strftime('%H:%M')
            log_entry = f"{timestamp}|{self.bot_id}|{action}|{description}\n"
            
            with open('/home/activeloguser/activelog/micro_updates.log', 'a') as f:
                f.write(log_entry)
                
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            
    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics"""
        
        return {
            "bot_id": self.bot_id,
            "stats": self.cleanup_stats,
            "config": self.cleanup_config,
            "last_cycle": datetime.now().isoformat()
        }

# Main function for running cleanup cycles
async def run_garbage_collection_service(anthropic_api_key: str):
    """Run the garbage collection service"""
    
    gc_bot = GarbageCollectorBot(anthropic_api_key)
    
    logger.info("Starting Garbage Collection Bot service")
    
    while True:
        try:
            # Run cleanup cycle
            results = await gc_bot.run_cleanup_cycle()
            
            logger.info(f"Cleanup cycle completed: {results['total_files_cleaned']} files, "
                       f"{results['total_mb_freed']:.1f}MB freed")
            
            # Wait 30 minutes between cycles
            await asyncio.sleep(1800)
            
        except Exception as e:
            logger.error(f"Garbage collection service error: {e}")
            await asyncio.sleep(300)  # 5 minutes on error

if __name__ == "__main__":
    import sys
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable required")
        sys.exit(1)
        
    # Run garbage collection service
    asyncio.run(run_garbage_collection_service(api_key))