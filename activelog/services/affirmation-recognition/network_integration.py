#!/usr/bin/env python3
"""
Building Bots Network Integration Layer

This module handles integration with all services in the Building Bots Network,
enabling seamless feedback capture, pattern sharing, and continuous improvement
across the entire ecosystem.

Key Features:
- Service discovery and registration
- Real-time feedback propagation
- Cross-service pattern sharing
- Quality scoring and validation
- Network-wide performance monitoring
- Automatic service health checking
- Load balancing and failover
"""

import asyncio
import aiohttp
import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, deque
import time
import hashlib
import uuid
from enum import Enum

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    UNKNOWN = "unknown"

class FeedbackType(Enum):
    AFFIRMATION = "affirmation"
    CORRECTION = "correction"
    CLARIFICATION = "clarification"
    COMPLETION = "completion"
    ERROR = "error"

@dataclass
class ServiceInfo:
    service_name: str
    url: str
    status: ServiceStatus
    last_health_check: datetime
    response_time: float
    error_rate: float
    capabilities: List[str]
    version: str
    metadata: Dict[str, Any]

@dataclass
class NetworkFeedback:
    feedback_id: str
    user_id: str
    session_id: str
    source_service: str
    target_service: Optional[str]
    feedback_type: FeedbackType
    content: str
    context: Dict[str, Any]
    confidence_score: float
    timestamp: datetime
    processed: bool = False

@dataclass
class ServicePattern:
    pattern_id: str
    service_name: str
    pattern_type: str
    input_pattern: str
    output_pattern: str
    success_rate: float
    usage_count: int
    confidence: float
    created_at: datetime
    last_used: datetime

@dataclass
class NetworkInsight:
    insight_id: str
    insight_type: str
    source_services: List[str]
    description: str
    impact_score: float
    actionable_recommendations: List[str]
    supporting_data: Dict[str, Any]
    created_at: datetime

class ServiceDiscovery:
    """Discovers and monitors services in the Building Bots Network"""
    
    def __init__(self):
        self.services = {}
        self.discovery_endpoints = [
            "http://localhost:8470/health",  # AI Picker System
            "http://localhost:8471/health",  # Hierarchical Task System
            "http://localhost:8474/health",  # Claude Task Hierarchy
            "http://localhost:8475/health",  # OpenAI Integration
            "http://localhost:8473/health",  # Resource Monitor
            "http://localhost:8500/health",  # Generative Tools Hub
            "http://localhost:8480/health",  # Image Generation
            "http://localhost:8481/health",  # Audio Generation
            "http://localhost:8483/health",  # Video Generation
            "http://localhost:8482/health",  # Code Generation
        ]
        self.health_check_interval = 30  # 30 seconds
        self.is_running = False
        
    async def start_discovery(self):
        """Start the service discovery process"""
        self.is_running = True
        while self.is_running:
            await self._discover_services()
            await asyncio.sleep(self.health_check_interval)
    
    async def _discover_services(self):
        """Discover and health-check all services"""
        tasks = []
        for endpoint in self.discovery_endpoints:
            task = self._check_service_health(endpoint)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for endpoint, result in zip(self.discovery_endpoints, results):
            if isinstance(result, Exception):
                self._mark_service_offline(endpoint)
            else:
                self._update_service_info(endpoint, result)
    
    async def _check_service_health(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Check health of a single service"""
        try:
            start_time = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=5) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        data = await response.json()
                        data['response_time'] = response_time
                        return data
                    else:
                        logger.warning(f"Service health check failed: {endpoint} (status: {response.status})")
                        return None
                        
        except Exception as e:
            logger.warning(f"Service health check error: {endpoint} - {e}")
            return None
    
    def _update_service_info(self, endpoint: str, health_data: Dict[str, Any]):
        """Update service information"""
        service_name = self._extract_service_name(endpoint, health_data)
        
        # Determine status
        status = ServiceStatus.HEALTHY
        if health_data.get('response_time', 0) > 5.0:
            status = ServiceStatus.DEGRADED
        
        service_info = ServiceInfo(
            service_name=service_name,
            url=endpoint.replace('/health', ''),
            status=status,
            last_health_check=datetime.now(),
            response_time=health_data.get('response_time', 0),
            error_rate=0.0,  # Would be calculated from historical data
            capabilities=health_data.get('capabilities', []),
            version=health_data.get('version', 'unknown'),
            metadata=health_data
        )
        
        self.services[service_name] = service_info
        logger.debug(f"Updated service info: {service_name}")
    
    def _mark_service_offline(self, endpoint: str):
        """Mark a service as offline"""
        service_name = self._extract_service_name(endpoint, {})
        
        if service_name in self.services:
            self.services[service_name].status = ServiceStatus.OFFLINE
            self.services[service_name].last_health_check = datetime.now()
    
    def _extract_service_name(self, endpoint: str, health_data: Dict[str, Any]) -> str:
        """Extract service name from endpoint or health data"""
        # Try to get from health data first
        if 'service_name' in health_data:
            return health_data['service_name']
        
        # Extract from endpoint
        port_map = {
            '8470': 'ai-picker-system',
            '8471': 'hierarchical-task-system',
            '8474': 'claude-task-hierarchy',
            '8475': 'openai-integration',
            '8473': 'resource-monitor',
            '8500': 'generative-tools-hub',
            '8480': 'image-generation',
            '8481': 'audio-generation',
            '8483': 'video-generation',
            '8482': 'code-generation'
        }
        
        for port, name in port_map.items():
            if port in endpoint:
                return name
        
        return 'unknown-service'
    
    def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services"""
        return [
            service for service in self.services.values()
            if service.status == ServiceStatus.HEALTHY
        ]
    
    def get_service(self, service_name: str) -> Optional[ServiceInfo]:
        """Get service information by name"""
        return self.services.get(service_name)
    
    def stop_discovery(self):
        """Stop the service discovery process"""
        self.is_running = False

class FeedbackCollector:
    """Collects feedback from all services in the network"""
    
    def __init__(self, service_discovery: ServiceDiscovery):
        self.service_discovery = service_discovery
        self.feedback_buffer = deque(maxlen=10000)
        self.feedback_handlers = {}
        self.collection_stats = defaultdict(int)
        
    def register_feedback_handler(self, feedback_type: FeedbackType, handler):
        """Register a handler for specific feedback types"""
        self.feedback_handlers[feedback_type] = handler
    
    async def collect_feedback_from_service(self, service_name: str) -> List[NetworkFeedback]:
        """Collect feedback from a specific service"""
        service = self.service_discovery.get_service(service_name)
        if not service or service.status != ServiceStatus.HEALTHY:
            return []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{service.url}/feedback/recent", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        feedback_list = []
                        
                        for feedback_data in data.get('feedback', []):
                            feedback = self._parse_feedback(feedback_data, service_name)
                            if feedback:
                                feedback_list.append(feedback)
                                self.feedback_buffer.append(feedback)
                        
                        self.collection_stats[service_name] += len(feedback_list)
                        return feedback_list
                    
        except Exception as e:
            logger.warning(f"Failed to collect feedback from {service_name}: {e}")
        
        return []
    
    def _parse_feedback(self, data: Dict[str, Any], source_service: str) -> Optional[NetworkFeedback]:
        """Parse feedback data into NetworkFeedback object"""
        try:
            return NetworkFeedback(
                feedback_id=data.get('feedback_id', str(uuid.uuid4())),
                user_id=data['user_id'],
                session_id=data.get('session_id', ''),
                source_service=source_service,
                target_service=data.get('target_service'),
                feedback_type=FeedbackType(data.get('feedback_type', 'affirmation')),
                content=data['content'],
                context=data.get('context', {}),
                confidence_score=data.get('confidence_score', 0.0),
                timestamp=datetime.fromisoformat(data['timestamp']),
                processed=False
            )
        except Exception as e:
            logger.warning(f"Failed to parse feedback: {e}")
            return None
    
    async def process_feedback(self, feedback: NetworkFeedback):
        """Process a feedback item"""
        if feedback.feedback_type in self.feedback_handlers:
            handler = self.feedback_handlers[feedback.feedback_type]
            try:
                await handler(feedback)
                feedback.processed = True
                logger.debug(f"Processed feedback: {feedback.feedback_id}")
            except Exception as e:
                logger.error(f"Error processing feedback {feedback.feedback_id}: {e}")
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback collection statistics"""
        return {
            'total_feedback_items': len(self.feedback_buffer),
            'collection_stats_by_service': dict(self.collection_stats),
            'feedback_types': dict(defaultdict(int, {
                fb.feedback_type.value: 1 for fb in self.feedback_buffer
            })),
            'recent_activity': len([
                fb for fb in self.feedback_buffer 
                if fb.timestamp > datetime.now() - timedelta(hours=1)
            ])
        }

class PatternDistribution:
    """Distributes learned patterns across the network"""
    
    def __init__(self, service_discovery: ServiceDiscovery):
        self.service_discovery = service_discovery
        self.pattern_cache = {}
        self.distribution_history = []
        self.success_rates = defaultdict(float)
        
    async def distribute_pattern(self, pattern: ServicePattern, target_services: List[str] = None) -> Dict[str, bool]:
        """Distribute a pattern to target services"""
        if target_services is None:
            target_services = [s.service_name for s in self.service_discovery.get_healthy_services()]
        
        results = {}
        tasks = []
        
        for service_name in target_services:
            if service_name != pattern.service_name:  # Don't send back to source
                task = self._send_pattern_to_service(pattern, service_name)
                tasks.append((service_name, task))
        
        task_results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        for (service_name, _), result in zip(tasks, task_results):
            if isinstance(result, Exception):
                results[service_name] = False
                logger.warning(f"Failed to send pattern to {service_name}: {result}")
            else:
                results[service_name] = result
                if result:
                    self._update_success_rate(service_name, True)
                else:
                    self._update_success_rate(service_name, False)
        
        # Record distribution
        self.distribution_history.append({
            'pattern_id': pattern.pattern_id,
            'timestamp': datetime.now(),
            'targets': target_services,
            'results': results,
            'success_rate': sum(results.values()) / len(results) if results else 0
        })
        
        return results
    
    async def _send_pattern_to_service(self, pattern: ServicePattern, service_name: str) -> bool:
        """Send a pattern to a specific service"""
        service = self.service_discovery.get_service(service_name)
        if not service or service.status != ServiceStatus.HEALTHY:
            return False
        
        try:
            pattern_data = asdict(pattern)
            # Convert datetime objects to ISO strings
            pattern_data['created_at'] = pattern.created_at.isoformat()
            pattern_data['last_used'] = pattern.last_used.isoformat()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{service.url}/patterns/receive",
                    json=pattern_data,
                    timeout=15
                ) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.warning(f"Failed to send pattern to {service_name}: {e}")
            return False
    
    def _update_success_rate(self, service_name: str, success: bool):
        """Update success rate for pattern distribution"""
        current_rate = self.success_rates[service_name]
        # Use exponential moving average
        alpha = 0.1
        new_rate = current_rate * (1 - alpha) + (1.0 if success else 0.0) * alpha
        self.success_rates[service_name] = new_rate
    
    async def request_patterns_from_service(self, service_name: str, pattern_type: str = None) -> List[ServicePattern]:
        """Request patterns from a specific service"""
        service = self.service_discovery.get_service(service_name)
        if not service or service.status != ServiceStatus.HEALTHY:
            return []
        
        try:
            params = {}
            if pattern_type:
                params['pattern_type'] = pattern_type
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{service.url}/patterns/export",
                    params=params,
                    timeout=15
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        patterns = []
                        
                        for pattern_data in data.get('patterns', []):
                            pattern = self._parse_service_pattern(pattern_data)
                            if pattern:
                                patterns.append(pattern)
                        
                        return patterns
                        
        except Exception as e:
            logger.warning(f"Failed to request patterns from {service_name}: {e}")
        
        return []
    
    def _parse_service_pattern(self, data: Dict[str, Any]) -> Optional[ServicePattern]:
        """Parse service pattern data"""
        try:
            return ServicePattern(
                pattern_id=data['pattern_id'],
                service_name=data['service_name'],
                pattern_type=data['pattern_type'],
                input_pattern=data['input_pattern'],
                output_pattern=data['output_pattern'],
                success_rate=data['success_rate'],
                usage_count=data['usage_count'],
                confidence=data['confidence'],
                created_at=datetime.fromisoformat(data['created_at']),
                last_used=datetime.fromisoformat(data['last_used'])
            )
        except Exception as e:
            logger.warning(f"Failed to parse service pattern: {e}")
            return None
    
    def get_distribution_stats(self) -> Dict[str, Any]:
        """Get pattern distribution statistics"""
        if not self.distribution_history:
            return {"total_distributions": 0}
        
        recent_distributions = [
            d for d in self.distribution_history
            if d['timestamp'] > datetime.now() - timedelta(hours=24)
        ]
        
        return {
            'total_distributions': len(self.distribution_history),
            'recent_distributions': len(recent_distributions),
            'average_success_rate': np.mean([d['success_rate'] for d in recent_distributions]) if recent_distributions else 0,
            'service_success_rates': dict(self.success_rates),
            'last_distribution': self.distribution_history[-1]['timestamp'].isoformat() if self.distribution_history else None
        }

class QualityScoring:
    """Scores the quality of interactions and improvements across the network"""
    
    def __init__(self):
        self.scoring_models = {}
        self.quality_history = defaultdict(list)
        self.baseline_metrics = {}
        
    def calculate_interaction_quality(self, feedback: NetworkFeedback, context: Dict[str, Any]) -> float:
        """Calculate quality score for an interaction"""
        score = 0.0
        
        # Base score from confidence
        score += feedback.confidence_score * 0.4
        
        # Context relevance (simplified)
        context_score = self._assess_context_relevance(feedback, context)
        score += context_score * 0.3
        
        # Response time factor
        response_time = context.get('response_time', 5.0)
        time_score = max(0, 1.0 - (response_time - 1.0) / 10.0)  # Penalize slow responses
        score += time_score * 0.2
        
        # User satisfaction indicators
        satisfaction_score = self._extract_satisfaction_signals(feedback)
        score += satisfaction_score * 0.1
        
        return min(max(score, 0.0), 1.0)  # Clamp between 0 and 1
    
    def _assess_context_relevance(self, feedback: NetworkFeedback, context: Dict[str, Any]) -> float:
        """Assess how relevant the feedback is to the context"""
        # This would implement sophisticated context analysis
        # For now, return a simple heuristic
        
        if not context:
            return 0.5
        
        # Check if feedback is recent relative to the interaction
        if 'interaction_timestamp' in context:
            interaction_time = datetime.fromisoformat(context['interaction_timestamp'])
            time_diff = (feedback.timestamp - interaction_time).total_seconds()
            
            if time_diff < 30:  # Very recent
                return 0.9
            elif time_diff < 300:  # Within 5 minutes
                return 0.7
            elif time_diff < 3600:  # Within 1 hour
                return 0.5
            else:
                return 0.2
        
        return 0.6  # Default moderate relevance
    
    def _extract_satisfaction_signals(self, feedback: NetworkFeedback) -> float:
        """Extract satisfaction signals from feedback content"""
        content = feedback.content.lower()
        
        # Positive indicators
        positive_words = ['perfect', 'excellent', 'great', 'awesome', 'love', 'exactly', 'right']
        positive_score = sum(1 for word in positive_words if word in content) * 0.15
        
        # Negative indicators
        negative_words = ['wrong', 'bad', 'terrible', 'hate', 'awful', 'incorrect', 'useless']
        negative_score = sum(1 for word in negative_words if word in content) * 0.2
        
        # Punctuation indicators
        if '!' in content:
            positive_score += 0.1
        if '?' in content:
            positive_score -= 0.05  # Slight penalty for uncertainty
        
        return max(0, positive_score - negative_score)
    
    def update_service_quality_baseline(self, service_name: str, metrics: Dict[str, float]):
        """Update quality baseline for a service"""
        if service_name not in self.baseline_metrics:
            self.baseline_metrics[service_name] = {}
        
        for metric, value in metrics.items():
            if metric not in self.baseline_metrics[service_name]:
                self.baseline_metrics[service_name][metric] = value
            else:
                # Use exponential moving average
                alpha = 0.1
                current = self.baseline_metrics[service_name][metric]
                self.baseline_metrics[service_name][metric] = current * (1 - alpha) + value * alpha
    
    def calculate_improvement_score(self, service_name: str, before_metrics: Dict[str, float], 
                                  after_metrics: Dict[str, float]) -> float:
        """Calculate improvement score for a service"""
        if not before_metrics or not after_metrics:
            return 0.0
        
        improvements = []
        
        for metric in before_metrics:
            if metric in after_metrics:
                before_value = before_metrics[metric]
                after_value = after_metrics[metric]
                
                if before_value > 0:
                    improvement = (after_value - before_value) / before_value
                    improvements.append(improvement)
        
        if not improvements:
            return 0.0
        
        # Calculate weighted average improvement
        avg_improvement = np.mean(improvements)
        
        # Convert to 0-1 score
        # Assume 20% improvement = 1.0 score
        return min(max(avg_improvement / 0.2, -1.0), 1.0)

class NetworkAnalytics:
    """Provides analytics and insights across the Building Bots Network"""
    
    def __init__(self, service_discovery: ServiceDiscovery, feedback_collector: FeedbackCollector,
                 pattern_distribution: PatternDistribution, quality_scoring: QualityScoring):
        self.service_discovery = service_discovery
        self.feedback_collector = feedback_collector
        self.pattern_distribution = pattern_distribution
        self.quality_scoring = quality_scoring
        self.insights_cache = []
        
    def generate_network_insights(self) -> List[NetworkInsight]:
        """Generate insights about the entire network"""
        insights = []
        
        # Service health insights
        health_insight = self._analyze_service_health()
        if health_insight:
            insights.append(health_insight)
        
        # Feedback patterns insight
        feedback_insight = self._analyze_feedback_patterns()
        if feedback_insight:
            insights.append(feedback_insight)
        
        # Performance insights
        performance_insight = self._analyze_performance_trends()
        if performance_insight:
            insights.append(performance_insight)
        
        # Pattern distribution insights
        distribution_insight = self._analyze_pattern_distribution()
        if distribution_insight:
            insights.append(distribution_insight)
        
        self.insights_cache.extend(insights)
        return insights
    
    def _analyze_service_health(self) -> Optional[NetworkInsight]:
        """Analyze overall service health"""
        services = list(self.service_discovery.services.values())
        if not services:
            return None
        
        healthy_count = len([s for s in services if s.status == ServiceStatus.HEALTHY])
        total_count = len(services)
        health_percentage = healthy_count / total_count
        
        if health_percentage < 0.8:  # Less than 80% healthy
            return NetworkInsight(
                insight_id=str(uuid.uuid4()),
                insight_type="service_health_alert",
                source_services=[s.service_name for s in services if s.status != ServiceStatus.HEALTHY],
                description=f"Network health degraded: {healthy_count}/{total_count} services healthy",
                impact_score=1.0 - health_percentage,
                actionable_recommendations=[
                    "Check unhealthy services for errors",
                    "Consider scaling resources",
                    "Review network connectivity"
                ],
                supporting_data={
                    "healthy_services": healthy_count,
                    "total_services": total_count,
                    "health_percentage": health_percentage,
                    "unhealthy_services": [s.service_name for s in services if s.status != ServiceStatus.HEALTHY]
                },
                created_at=datetime.now()
            )
        
        return None
    
    def _analyze_feedback_patterns(self) -> Optional[NetworkInsight]:
        """Analyze feedback patterns across services"""
        feedback_stats = self.feedback_collector.get_feedback_stats()
        
        if feedback_stats['total_feedback_items'] < 10:
            return None
        
        # Look for services with low feedback
        service_feedback = feedback_stats.get('collection_stats_by_service', {})
        avg_feedback = np.mean(list(service_feedback.values())) if service_feedback else 0
        
        low_feedback_services = [
            service for service, count in service_feedback.items()
            if count < avg_feedback * 0.5
        ]
        
        if low_feedback_services:
            return NetworkInsight(
                insight_id=str(uuid.uuid4()),
                insight_type="feedback_pattern_analysis",
                source_services=low_feedback_services,
                description=f"Low feedback from {len(low_feedback_services)} services",
                impact_score=0.6,
                actionable_recommendations=[
                    "Investigate user engagement with low-feedback services",
                    "Improve feedback collection mechanisms",
                    "Consider service optimization"
                ],
                supporting_data={
                    "low_feedback_services": low_feedback_services,
                    "average_feedback": avg_feedback,
                    "feedback_distribution": service_feedback
                },
                created_at=datetime.now()
            )
        
        return None
    
    def _analyze_performance_trends(self) -> Optional[NetworkInsight]:
        """Analyze performance trends"""
        services = self.service_discovery.get_healthy_services()
        slow_services = [s for s in services if s.response_time > 3.0]
        
        if slow_services:
            return NetworkInsight(
                insight_id=str(uuid.uuid4()),
                insight_type="performance_trend_analysis",
                source_services=[s.service_name for s in slow_services],
                description=f"Performance degradation detected in {len(slow_services)} services",
                impact_score=0.7,
                actionable_recommendations=[
                    "Optimize slow services",
                    "Check resource utilization",
                    "Consider load balancing"
                ],
                supporting_data={
                    "slow_services": [(s.service_name, s.response_time) for s in slow_services],
                    "average_response_time": np.mean([s.response_time for s in services])
                },
                created_at=datetime.now()
            )
        
        return None
    
    def _analyze_pattern_distribution(self) -> Optional[NetworkInsight]:
        """Analyze pattern distribution effectiveness"""
        distribution_stats = self.pattern_distribution.get_distribution_stats()
        
        if distribution_stats['total_distributions'] > 0:
            success_rate = distribution_stats['average_success_rate']
            
            if success_rate < 0.7:  # Less than 70% success
                return NetworkInsight(
                    insight_id=str(uuid.uuid4()),
                    insight_type="pattern_distribution_analysis",
                    source_services=list(distribution_stats.get('service_success_rates', {}).keys()),
                    description=f"Pattern distribution success rate is low: {success_rate:.1%}",
                    impact_score=0.8,
                    actionable_recommendations=[
                        "Review pattern distribution mechanisms",
                        "Improve service communication protocols",
                        "Optimize pattern formats"
                    ],
                    supporting_data=distribution_stats,
                    created_at=datetime.now()
                )
        
        return None
    
    def get_network_summary(self) -> Dict[str, Any]:
        """Get comprehensive network summary"""
        services = list(self.service_discovery.services.values())
        feedback_stats = self.feedback_collector.get_feedback_stats()
        distribution_stats = self.pattern_distribution.get_distribution_stats()
        
        return {
            'network_overview': {
                'total_services': len(services),
                'healthy_services': len([s for s in services if s.status == ServiceStatus.HEALTHY]),
                'average_response_time': np.mean([s.response_time for s in services]) if services else 0,
                'last_health_check': max([s.last_health_check for s in services]).isoformat() if services else None
            },
            'feedback_summary': feedback_stats,
            'pattern_distribution_summary': distribution_stats,
            'recent_insights': [asdict(insight) for insight in self.insights_cache[-5:]],  # Last 5 insights
            'network_health_score': self._calculate_network_health_score(),
            'generated_at': datetime.now().isoformat()
        }
    
    def _calculate_network_health_score(self) -> float:
        """Calculate overall network health score"""
        services = list(self.service_discovery.services.values())
        if not services:
            return 0.0
        
        # Service health component (50%)
        healthy_ratio = len([s for s in services if s.status == ServiceStatus.HEALTHY]) / len(services)
        health_component = healthy_ratio * 0.5
        
        # Performance component (30%)
        avg_response_time = np.mean([s.response_time for s in services])
        performance_component = max(0, 1.0 - (avg_response_time - 1.0) / 10.0) * 0.3
        
        # Feedback activity component (20%)
        feedback_stats = self.feedback_collector.get_feedback_stats()
        feedback_activity = min(feedback_stats.get('recent_activity', 0) / 100, 1.0) * 0.2
        
        return health_component + performance_component + feedback_activity

class BuildingBotsNetworkIntegration:
    """Main integration orchestrator for the Building Bots Network"""
    
    def __init__(self):
        self.service_discovery = ServiceDiscovery()
        self.feedback_collector = FeedbackCollector(self.service_discovery)
        self.pattern_distribution = PatternDistribution(self.service_discovery)
        self.quality_scoring = QualityScoring()
        self.analytics = NetworkAnalytics(
            self.service_discovery, self.feedback_collector,
            self.pattern_distribution, self.quality_scoring
        )
        
        self.is_running = False
        self.background_tasks = set()
        
    async def initialize(self):
        """Initialize the network integration"""
        logger.info("Initializing Building Bots Network Integration...")
        
        # Start service discovery
        discovery_task = asyncio.create_task(self.service_discovery.start_discovery())
        self.background_tasks.add(discovery_task)
        
        # Wait a bit for initial service discovery
        await asyncio.sleep(2)
        
        # Start other background tasks
        feedback_task = asyncio.create_task(self._feedback_collection_loop())
        self.background_tasks.add(feedback_task)
        
        analytics_task = asyncio.create_task(self._analytics_loop())
        self.background_tasks.add(analytics_task)
        
        self.is_running = True
        logger.info("Building Bots Network Integration initialized")
    
    async def _feedback_collection_loop(self):
        """Background loop for collecting feedback"""
        while self.is_running:
            try:
                healthy_services = self.service_discovery.get_healthy_services()
                
                for service in healthy_services:
                    feedback_list = await self.feedback_collector.collect_feedback_from_service(service.service_name)
                    
                    for feedback in feedback_list:
                        await self.feedback_collector.process_feedback(feedback)
                
                await asyncio.sleep(60)  # Collect feedback every minute
                
            except Exception as e:
                logger.error(f"Error in feedback collection loop: {e}")
                await asyncio.sleep(60)
    
    async def _analytics_loop(self):
        """Background loop for generating analytics insights"""
        while self.is_running:
            try:
                insights = self.analytics.generate_network_insights()
                if insights:
                    logger.info(f"Generated {len(insights)} network insights")
                
                await asyncio.sleep(300)  # Generate insights every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                await asyncio.sleep(300)
    
    async def distribute_learning_pattern(self, pattern: ServicePattern, target_services: List[str] = None) -> Dict[str, bool]:
        """Distribute a learning pattern across the network"""
        return await self.pattern_distribution.distribute_pattern(pattern, target_services)
    
    async def collect_patterns_from_network(self, pattern_type: str = None) -> Dict[str, List[ServicePattern]]:
        """Collect patterns from all services in the network"""
        results = {}
        healthy_services = self.service_discovery.get_healthy_services()
        
        for service in healthy_services:
            patterns = await self.pattern_distribution.request_patterns_from_service(
                service.service_name, pattern_type
            )
            if patterns:
                results[service.service_name] = patterns
        
        return results
    
    def calculate_interaction_quality(self, feedback: NetworkFeedback, context: Dict[str, Any]) -> float:
        """Calculate quality score for an interaction"""
        return self.quality_scoring.calculate_interaction_quality(feedback, context)
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get comprehensive network status"""
        return self.analytics.get_network_summary()
    
    async def shutdown(self):
        """Shutdown the network integration"""
        logger.info("Shutting down Building Bots Network Integration...")
        self.is_running = False
        
        # Stop service discovery
        self.service_discovery.stop_discovery()
        
        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        logger.info("Building Bots Network Integration shutdown complete")