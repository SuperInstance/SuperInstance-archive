#!/usr/bin/env python3
"""
Building Bots Network Integration Module

This module handles integration with the Building Bots Network hub and
other network services, implementing the principles of construction excellence,
continuous learning, and cross-service collaboration.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import aiohttp
from config import get_config, BuildingBotsNetworkConfig

logger = logging.getLogger("bbn-integration")

@dataclass
class NetworkServiceInfo:
    """Information about a network service"""
    name: str
    version: str
    endpoint: str
    capabilities: List[str]
    quality_level: str
    last_seen: datetime
    health_status: str

@dataclass
class QualityMetrics:
    """Quality metrics for network reporting"""
    service_name: str
    timestamp: datetime
    generation_count: int
    average_quality_score: float
    average_response_time: float
    success_rate: float
    security_issues_detected: int
    performance_optimizations: int
    user_satisfaction: float
    construction_excellence_score: float

@dataclass
class LearningInsight:
    """Cross-service learning insight"""
    source_service: str
    insight_type: str
    language: str
    pattern: str
    quality_improvement: float
    usage_count: int
    confidence_score: float
    timestamp: datetime

class BuildingBotsNetworkClient:
    """Client for Building Bots Network hub communication"""
    
    def __init__(self, config: BuildingBotsNetworkConfig):
        self.config = config
        self.hub_endpoint = config.hub_endpoint
        self.service_name = config.service_name
        self.service_version = config.service_version
        self.session = None
        self.registered = False
        self.last_heartbeat = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def register_service(self) -> bool:
        """Register this service with the Building Bots Network hub"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            registration_data = {
                "name": self.service_name,
                "version": self.service_version,
                "endpoint": f"http://localhost:8000",  # This service's endpoint
                "capabilities": [
                    "code-generation",
                    "multi-language-support",
                    "ai-provider-integration",
                    "quality-analysis",
                    "security-scanning",
                    "performance-optimization",
                    "test-generation",
                    "documentation-generation",
                    "code-refactoring",
                    "ml-intelligence"
                ],
                "quality_level": self.config.quality_standards_level,
                "construction_principles": self.config.construction_principles,
                "service_type": "code-generation",
                "supported_languages": [
                    "python", "javascript", "typescript", "rust", "go", "java",
                    "cpp", "csharp", "php", "ruby", "swift", "kotlin", "scala",
                    "clojure", "haskell", "html", "css", "sql"
                ],
                "supported_frameworks": [
                    "react", "vue", "angular", "fastapi", "django", "flask",
                    "express", "spring", "rails", "laravel", "nextjs", "nuxtjs",
                    "svelte", "flutter", "react_native"
                ]
            }
            
            async with self.session.post(
                f"{self.hub_endpoint}/services/register",
                json=registration_data
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    self.registered = True
                    logger.info(f"Successfully registered with Building Bots Network hub")
                    logger.info(f"Service ID: {result.get('service_id', 'unknown')}")
                    return True
                else:
                    logger.warning(f"Failed to register with hub: {response.status}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Failed to register with Building Bots Network hub: {e}")
            return False
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to the hub"""
        try:
            if not self.session:
                return False
            
            heartbeat_data = {
                "service_name": self.service_name,
                "timestamp": datetime.now().isoformat(),
                "status": "healthy",
                "metrics": await self._collect_service_metrics()
            }
            
            async with self.session.post(
                f"{self.hub_endpoint}/services/heartbeat",
                json=heartbeat_data
            ) as response:
                if response.status == 200:
                    self.last_heartbeat = datetime.now()
                    return True
                else:
                    logger.warning(f"Heartbeat failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Failed to send heartbeat: {e}")
            return False
    
    async def report_quality_metrics(self, metrics: QualityMetrics) -> bool:
        """Report quality metrics to the network"""
        try:
            if not self.session:
                return False
            
            await self.session.post(
                f"{self.hub_endpoint}/metrics/quality",
                json=asdict(metrics)
            )
            return True
            
        except Exception as e:
            logger.warning(f"Failed to report quality metrics: {e}")
            return False
    
    async def share_learning_insight(self, insight: LearningInsight) -> bool:
        """Share learning insight with the network"""
        try:
            if not self.session:
                return False
            
            await self.session.post(
                f"{self.hub_endpoint}/learning/insights",
                json=asdict(insight)
            )
            return True
            
        except Exception as e:
            logger.warning(f"Failed to share learning insight: {e}")
            return False
    
    async def get_network_insights(self, language: str = None) -> List[LearningInsight]:
        """Get learning insights from other network services"""
        try:
            if not self.session:
                return []
            
            params = {"service_type": "code-generation"}
            if language:
                params["language"] = language
            
            async with self.session.get(
                f"{self.hub_endpoint}/learning/insights",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        LearningInsight(**insight) 
                        for insight in data.get("insights", [])
                    ]
                
        except Exception as e:
            logger.warning(f"Failed to get network insights: {e}")
        
        return []
    
    async def discover_services(self, service_type: str = None) -> List[NetworkServiceInfo]:
        """Discover other services in the network"""
        try:
            if not self.session:
                return []
            
            params = {}
            if service_type:
                params["type"] = service_type
            
            async with self.session.get(
                f"{self.hub_endpoint}/services/discover",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return [
                        NetworkServiceInfo(**service) 
                        for service in data.get("services", [])
                    ]
                
        except Exception as e:
            logger.warning(f"Failed to discover services: {e}")
        
        return []
    
    async def get_construction_standards(self) -> Dict[str, Any]:
        """Get network-wide construction standards"""
        try:
            if not self.session:
                return {}
            
            async with self.session.get(
                f"{self.hub_endpoint}/standards/construction"
            ) as response:
                if response.status == 200:
                    return await response.json()
                
        except Exception as e:
            logger.warning(f"Failed to get construction standards: {e}")
        
        return {}
    
    async def _collect_service_metrics(self) -> Dict[str, Any]:
        """Collect current service metrics for heartbeat"""
        # This would integrate with your actual metrics collection
        return {
            "uptime_seconds": 3600,  # Placeholder
            "requests_processed": 100,  # Placeholder
            "average_response_time": 2.5,  # Placeholder
            "success_rate": 0.95,  # Placeholder
            "quality_score": 0.85,  # Placeholder
            "memory_usage_mb": 256,  # Placeholder
            "cpu_usage_percent": 15.5  # Placeholder
        }

class CrossServiceLearning:
    """Implements cross-service learning capabilities"""
    
    def __init__(self, network_client: BuildingBotsNetworkClient):
        self.network_client = network_client
        self.learned_patterns = {}
        self.quality_improvements = {}
        
    async def learn_from_generation(self, 
                                   code: str, 
                                   language: str, 
                                   quality_score: float,
                                   user_feedback: Optional[float] = None):
        """Learn from a code generation result"""
        try:
            # Extract patterns from high-quality code
            if quality_score >= 0.8:
                patterns = self._extract_code_patterns(code, language)
                
                for pattern in patterns:
                    key = f"{language}_{pattern['type']}"
                    if key not in self.learned_patterns:
                        self.learned_patterns[key] = []
                    
                    self.learned_patterns[key].append({
                        "pattern": pattern["pattern"],
                        "quality_score": quality_score,
                        "timestamp": datetime.now(),
                        "user_feedback": user_feedback
                    })
            
            # Share insights with network
            if quality_score >= 0.9 and user_feedback and user_feedback >= 0.8:
                insight = LearningInsight(
                    source_service=self.network_client.service_name,
                    insight_type="high_quality_pattern",
                    language=language,
                    pattern=code[:500],  # First 500 chars as pattern sample
                    quality_improvement=quality_score - 0.7,  # Improvement over baseline
                    usage_count=1,
                    confidence_score=min(quality_score, user_feedback or quality_score),
                    timestamp=datetime.now()
                )
                
                await self.network_client.share_learning_insight(insight)
                
        except Exception as e:
            logger.warning(f"Failed to learn from generation: {e}")
    
    async def apply_network_insights(self, language: str, prompt: str) -> str:
        """Apply insights from network learning to improve generation"""
        try:
            insights = await self.network_client.get_network_insights(language)
            
            if not insights:
                return prompt
            
            # Filter relevant insights
            relevant_insights = [
                insight for insight in insights
                if insight.confidence_score >= 0.7 and 
                insight.quality_improvement >= 0.1
            ]
            
            if not relevant_insights:
                return prompt
            
            # Enhance prompt with insights
            enhancement = "\n\nBuilding Bots Network Insights:\n"
            enhancement += "Apply these proven patterns for high-quality code:\n"
            
            for insight in relevant_insights[:3]:  # Top 3 insights
                enhancement += f"- {insight.insight_type}: {insight.pattern[:100]}...\n"
            
            enhanced_prompt = prompt + enhancement
            return enhanced_prompt
            
        except Exception as e:
            logger.warning(f"Failed to apply network insights: {e}")
            return prompt
    
    def _extract_code_patterns(self, code: str, language: str) -> List[Dict[str, str]]:
        """Extract reusable patterns from high-quality code"""
        patterns = []
        
        try:
            lines = code.split('\n')
            
            # Extract function patterns
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Function definitions
                if language == "python" and line_stripped.startswith("def "):
                    pattern_lines = lines[i:min(i+5, len(lines))]
                    patterns.append({
                        "type": "function_definition",
                        "pattern": '\n'.join(pattern_lines)
                    })
                
                # Error handling patterns
                elif "try:" in line_stripped or "except:" in line_stripped:
                    pattern_lines = lines[max(0, i-1):min(i+3, len(lines))]
                    patterns.append({
                        "type": "error_handling",
                        "pattern": '\n'.join(pattern_lines)
                    })
                
                # Documentation patterns
                elif line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                    pattern_lines = lines[i:min(i+3, len(lines))]
                    patterns.append({
                        "type": "documentation",
                        "pattern": '\n'.join(pattern_lines)
                    })
            
        except Exception as e:
            logger.warning(f"Pattern extraction failed: {e}")
        
        return patterns

class ConstructionExcellenceMonitor:
    """Monitors adherence to Building Bots Network construction excellence principles"""
    
    def __init__(self, network_client: BuildingBotsNetworkClient):
        self.network_client = network_client
        self.excellence_metrics = {
            "production_ready": 0.0,
            "best_practices": 0.0,
            "continuous_learning": 0.0,
            "security_first": 0.0,
            "performance_optimized": 0.0,
            "maintainable_code": 0.0,
            "comprehensive_testing": 0.0,
            "detailed_documentation": 0.0
        }
    
    async def evaluate_construction_excellence(self, 
                                             code: str, 
                                             language: str,
                                             has_tests: bool = False,
                                             has_docs: bool = False,
                                             security_score: float = 0.0,
                                             performance_score: float = 0.0) -> float:
        """Evaluate how well generated code meets construction excellence standards"""
        
        try:
            scores = {}
            
            # Production readiness (code quality, error handling)
            scores["production_ready"] = self._evaluate_production_readiness(code, language)
            
            # Best practices (code style, patterns)
            scores["best_practices"] = self._evaluate_best_practices(code, language)
            
            # Security first
            scores["security_first"] = security_score
            
            # Performance optimization
            scores["performance_optimized"] = performance_score
            
            # Maintainable code (structure, readability)
            scores["maintainable_code"] = self._evaluate_maintainability(code)
            
            # Testing
            scores["comprehensive_testing"] = 1.0 if has_tests else 0.0
            
            # Documentation
            scores["detailed_documentation"] = 1.0 if has_docs else 0.0
            
            # Continuous learning (this service's learning capability)
            scores["continuous_learning"] = 0.8  # Based on implemented learning features
            
            # Update running averages
            for principle, score in scores.items():
                current = self.excellence_metrics[principle]
                self.excellence_metrics[principle] = (current * 0.9) + (score * 0.1)
            
            # Calculate overall excellence score
            overall_score = sum(scores.values()) / len(scores)
            
            # Report to network if significant
            if overall_score >= 0.8:
                await self._report_excellence_achievement(scores)
            
            return overall_score
            
        except Exception as e:
            logger.warning(f"Construction excellence evaluation failed: {e}")
            return 0.5
    
    def _evaluate_production_readiness(self, code: str, language: str) -> float:
        """Evaluate production readiness of code"""
        score = 0.0
        
        # Check for error handling
        if "try" in code and "except" in code:
            score += 0.3
        
        # Check for input validation
        if any(keyword in code for keyword in ["validate", "check", "assert"]):
            score += 0.2
        
        # Check for logging
        if any(keyword in code for keyword in ["log", "logger", "print"]):
            score += 0.2
        
        # Check for type hints (Python)
        if language == "python" and "->" in code:
            score += 0.3
        
        return min(1.0, score)
    
    def _evaluate_best_practices(self, code: str, language: str) -> float:
        """Evaluate adherence to best practices"""
        score = 0.0
        lines = code.split('\n')
        
        # Check average line length
        avg_line_length = sum(len(line) for line in lines) / len(lines) if lines else 0
        if avg_line_length <= 100:
            score += 0.3
        
        # Check for meaningful variable names
        if any(len(word) > 3 for line in lines for word in line.split() if word.isalpha()):
            score += 0.3
        
        # Check for comments
        comment_ratio = len([line for line in lines if line.strip().startswith('#')]) / len(lines) if lines else 0
        score += min(0.4, comment_ratio * 2)
        
        return min(1.0, score)
    
    def _evaluate_maintainability(self, code: str) -> float:
        """Evaluate code maintainability"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        if not non_empty_lines:
            return 0.0
        
        score = 0.0
        
        # Function length check
        current_function_length = 0
        max_function_length = 0
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('function '):
                current_function_length = 0
            current_function_length += 1
            max_function_length = max(max_function_length, current_function_length)
        
        # Prefer shorter functions
        if max_function_length <= 20:
            score += 0.5
        elif max_function_length <= 50:
            score += 0.3
        
        # Nesting level check (simplified)
        max_indent = 0
        for line in lines:
            if line.strip():
                indent = len(line) - len(line.lstrip())
                max_indent = max(max_indent, indent // 4)  # Assuming 4-space indents
        
        # Prefer lower nesting levels
        if max_indent <= 3:
            score += 0.5
        elif max_indent <= 5:
            score += 0.3
        
        return min(1.0, score)
    
    async def _report_excellence_achievement(self, scores: Dict[str, float]):
        """Report construction excellence achievement to network"""
        try:
            excellence_report = {
                "service_name": self.network_client.service_name,
                "timestamp": datetime.now().isoformat(),
                "principle_scores": scores,
                "overall_score": sum(scores.values()) / len(scores),
                "achievement_type": "high_excellence_generation"
            }
            
            # This would be sent to the network hub
            # await self.network_client.report_excellence_achievement(excellence_report)
            logger.info(f"High construction excellence achieved: {excellence_report['overall_score']:.2f}")
            
        except Exception as e:
            logger.warning(f"Failed to report excellence achievement: {e}")

# Global network integration instance
_network_client = None
_cross_service_learning = None
_excellence_monitor = None

async def initialize_network_integration():
    """Initialize Building Bots Network integration"""
    global _network_client, _cross_service_learning, _excellence_monitor
    
    try:
        config = get_config()
        
        _network_client = BuildingBotsNetworkClient(config.bbn)
        await _network_client.__aenter__()
        
        # Register with network
        await _network_client.register_service()
        
        # Initialize learning and monitoring
        _cross_service_learning = CrossServiceLearning(_network_client)
        _excellence_monitor = ConstructionExcellenceMonitor(_network_client)
        
        # Start heartbeat task
        asyncio.create_task(_heartbeat_loop())
        
        logger.info("Building Bots Network integration initialized successfully")
        
    except Exception as e:
        logger.warning(f"Failed to initialize Building Bots Network integration: {e}")

async def _heartbeat_loop():
    """Periodic heartbeat to network hub"""
    global _network_client
    
    while _network_client:
        try:
            await _network_client.send_heartbeat()
            await asyncio.sleep(60)  # Heartbeat every minute
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")
            await asyncio.sleep(60)

def get_network_client() -> Optional[BuildingBotsNetworkClient]:
    """Get the network client instance"""
    return _network_client

def get_cross_service_learning() -> Optional[CrossServiceLearning]:
    """Get the cross-service learning instance"""
    return _cross_service_learning

def get_excellence_monitor() -> Optional[ConstructionExcellenceMonitor]:
    """Get the construction excellence monitor"""
    return _excellence_monitor