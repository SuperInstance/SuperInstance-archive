"""
Performance Optimization Advisor for SuperInstance
AI-powered system that analyzes application performance and provides intelligent optimization recommendations
"""

import time
import json
import psutil
import threading
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import statistics
import re
from collections import defaultdict, deque
import hashlib

class OptimizationType(Enum):
    MEMORY = "memory"
    CPU = "cpu"
    NETWORK = "network"
    DISK_IO = "disk_io"
    DATABASE = "database"
    ALGORITHM = "algorithm"
    CACHING = "caching"
    ARCHITECTURE = "architecture"

class Urgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ImpactLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    TRANSFORMATIVE = "transformative"

@dataclass
class PerformanceMetric:
    name: str
    value: float
    unit: str
    timestamp: float
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    trend_data: List[float] = None

@dataclass
class OptimizationRecommendation:
    id: str
    title: str
    description: str
    optimization_type: OptimizationType
    urgency: Urgency
    impact_level: ImpactLevel
    estimated_improvement: Dict[str, float]
    implementation_time: int  # hours
    implementation_complexity: str
    code_changes_required: List[Dict[str, Any]]
    configuration_changes: Dict[str, Any]
    dependencies_needed: List[str]
    rollback_plan: str
    success_metrics: List[str]
    confidence_score: float

@dataclass
class PerformanceBottleneck:
    component: str
    issue_type: str
    severity: Urgency
    description: str
    metrics: List[PerformanceMetric]
    root_cause: str
    recommendations: List[str]

@dataclass
class SystemProfile:
    cpu_cores: int
    memory_gb: float
    disk_type: str
    network_bandwidth: str
    application_type: str
    technology_stack: List[str]
    deployment_environment: str
    expected_load: Dict[str, Any]

class PerformanceProfiler:
    """Profiles application performance and collects metrics"""
    
    def __init__(self):
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.active_profiling = False
        self.profiling_thread = None
        self.sampling_interval = 1.0  # seconds
        
    def start_profiling(self, duration: Optional[int] = None):
        """Start continuous performance profiling"""
        if self.active_profiling:
            return
            
        self.active_profiling = True
        self.profiling_thread = threading.Thread(target=self._profiling_loop, args=(duration,))
        self.profiling_thread.start()
    
    def stop_profiling(self):
        """Stop performance profiling"""
        self.active_profiling = False
        if self.profiling_thread:
            self.profiling_thread.join()
    
    def get_current_metrics(self) -> Dict[str, PerformanceMetric]:
        """Get current system performance metrics"""
        metrics = {}
        current_time = time.time()
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics['cpu_usage'] = PerformanceMetric(
            name='CPU Usage',
            value=cpu_percent,
            unit='%',
            timestamp=current_time,
            threshold_warning=70.0,
            threshold_critical=90.0
        )
        
        # Memory metrics
        memory = psutil.virtual_memory()
        metrics['memory_usage'] = PerformanceMetric(
            name='Memory Usage',
            value=memory.percent,
            unit='%',
            timestamp=current_time,
            threshold_warning=75.0,
            threshold_critical=90.0
        )
        
        # Disk I/O metrics
        disk_io = psutil.disk_io_counters()
        if disk_io:
            metrics['disk_read_rate'] = PerformanceMetric(
                name='Disk Read Rate',
                value=disk_io.read_bytes / (1024 * 1024),  # MB/s approximation
                unit='MB/s',
                timestamp=current_time
            )
            
            metrics['disk_write_rate'] = PerformanceMetric(
                name='Disk Write Rate',
                value=disk_io.write_bytes / (1024 * 1024),  # MB/s approximation
                unit='MB/s',
                timestamp=current_time
            )
        
        # Network metrics
        network = psutil.net_io_counters()
        if network:
            metrics['network_sent'] = PerformanceMetric(
                name='Network Sent',
                value=network.bytes_sent / (1024 * 1024),  # MB
                unit='MB',
                timestamp=current_time
            )
            
            metrics['network_recv'] = PerformanceMetric(
                name='Network Received',
                value=network.bytes_recv / (1024 * 1024),  # MB
                unit='MB',
                timestamp=current_time
            )
        
        return metrics
    
    def analyze_application_metrics(self, app_metrics: Dict[str, Any]) -> Dict[str, PerformanceMetric]:
        """Analyze application-specific metrics"""
        metrics = {}
        current_time = time.time()
        
        # Response time metrics
        if 'response_times' in app_metrics:
            response_times = app_metrics['response_times']
            if response_times:
                avg_response = statistics.mean(response_times)
                metrics['avg_response_time'] = PerformanceMetric(
                    name='Average Response Time',
                    value=avg_response,
                    unit='ms',
                    timestamp=current_time,
                    threshold_warning=200.0,
                    threshold_critical=500.0
                )
                
                p95_response = sorted(response_times)[int(len(response_times) * 0.95)]
                metrics['p95_response_time'] = PerformanceMetric(
                    name='95th Percentile Response Time',
                    value=p95_response,
                    unit='ms',
                    timestamp=current_time,
                    threshold_warning=500.0,
                    threshold_critical=1000.0
                )
        
        # Throughput metrics
        if 'requests_per_second' in app_metrics:
            metrics['throughput'] = PerformanceMetric(
                name='Requests Per Second',
                value=app_metrics['requests_per_second'],
                unit='req/s',
                timestamp=current_time
            )
        
        # Error rate metrics
        if 'error_rate' in app_metrics:
            metrics['error_rate'] = PerformanceMetric(
                name='Error Rate',
                value=app_metrics['error_rate'] * 100,
                unit='%',
                timestamp=current_time,
                threshold_warning=1.0,
                threshold_critical=5.0
            )
        
        # Database metrics
        if 'db_query_times' in app_metrics:
            query_times = app_metrics['db_query_times']
            if query_times:
                avg_query_time = statistics.mean(query_times)
                metrics['avg_db_query_time'] = PerformanceMetric(
                    name='Average Database Query Time',
                    value=avg_query_time,
                    unit='ms',
                    timestamp=current_time,
                    threshold_warning=50.0,
                    threshold_critical=100.0
                )
        
        return metrics
    
    def _profiling_loop(self, duration: Optional[int]):
        """Main profiling loop"""
        start_time = time.time()
        
        while self.active_profiling:
            if duration and (time.time() - start_time) > duration:
                break
                
            try:
                # Collect system metrics
                metrics = self.get_current_metrics()
                
                # Store in history
                for metric_name, metric in metrics.items():
                    self.metrics_history[metric_name].append({
                        'timestamp': metric.timestamp,
                        'value': metric.value
                    })
                
                time.sleep(self.sampling_interval)
                
            except Exception as e:
                print(f"Error in profiling loop: {e}")
                time.sleep(1)
        
        self.active_profiling = False

class BottleneckDetector:
    """Detects performance bottlenecks in the system"""
    
    def __init__(self):
        self.detection_rules = self._load_detection_rules()
        
    def detect_bottlenecks(self, metrics: Dict[str, PerformanceMetric], 
                          historical_data: Dict[str, List[Dict[str, Any]]]) -> List[PerformanceBottleneck]:
        """Detect performance bottlenecks from metrics"""
        bottlenecks = []
        
        # CPU bottleneck detection
        cpu_bottleneck = self._detect_cpu_bottleneck(metrics, historical_data)
        if cpu_bottleneck:
            bottlenecks.append(cpu_bottleneck)
        
        # Memory bottleneck detection
        memory_bottleneck = self._detect_memory_bottleneck(metrics, historical_data)
        if memory_bottleneck:
            bottlenecks.append(memory_bottleneck)
        
        # I/O bottleneck detection
        io_bottleneck = self._detect_io_bottleneck(metrics, historical_data)
        if io_bottleneck:
            bottlenecks.append(io_bottleneck)
        
        # Database bottleneck detection
        db_bottleneck = self._detect_database_bottleneck(metrics, historical_data)
        if db_bottleneck:
            bottlenecks.append(db_bottleneck)
        
        # Network bottleneck detection
        network_bottleneck = self._detect_network_bottleneck(metrics, historical_data)
        if network_bottleneck:
            bottlenecks.append(network_bottleneck)
        
        return bottlenecks
    
    def _detect_cpu_bottleneck(self, metrics: Dict[str, PerformanceMetric], 
                              historical_data: Dict[str, List[Dict[str, Any]]]) -> Optional[PerformanceBottleneck]:
        """Detect CPU-related bottlenecks"""
        if 'cpu_usage' not in metrics:
            return None
        
        cpu_metric = metrics['cpu_usage']
        
        # High CPU usage
        if cpu_metric.value > 85:
            severity = Urgency.CRITICAL if cpu_metric.value > 95 else Urgency.HIGH
            
            # Analyze trend
            trend_analysis = self._analyze_trend(historical_data.get('cpu_usage', []))
            
            return PerformanceBottleneck(
                component='cpu',
                issue_type='high_usage',
                severity=severity,
                description=f'CPU usage is at {cpu_metric.value:.1f}%, which is above optimal levels',
                metrics=[cpu_metric],
                root_cause=self._determine_cpu_root_cause(cpu_metric.value, trend_analysis),
                recommendations=[
                    'Optimize CPU-intensive algorithms',
                    'Implement caching to reduce computational load',
                    'Consider horizontal scaling',
                    'Profile code to identify hot paths'
                ]
            )
        
        return None
    
    def _detect_memory_bottleneck(self, metrics: Dict[str, PerformanceMetric], 
                                 historical_data: Dict[str, List[Dict[str, Any]]]) -> Optional[PerformanceBottleneck]:
        """Detect memory-related bottlenecks"""
        if 'memory_usage' not in metrics:
            return None
        
        memory_metric = metrics['memory_usage']
        
        # High memory usage
        if memory_metric.value > 80:
            severity = Urgency.CRITICAL if memory_metric.value > 95 else Urgency.HIGH
            
            return PerformanceBottleneck(
                component='memory',
                issue_type='high_usage',
                severity=severity,
                description=f'Memory usage is at {memory_metric.value:.1f}%, approaching system limits',
                metrics=[memory_metric],
                root_cause=self._determine_memory_root_cause(memory_metric.value),
                recommendations=[
                    'Implement memory pooling',
                    'Optimize data structures',
                    'Add garbage collection tuning',
                    'Investigate memory leaks',
                    'Consider increasing available memory'
                ]
            )
        
        return None
    
    def _detect_io_bottleneck(self, metrics: Dict[str, PerformanceMetric], 
                             historical_data: Dict[str, List[Dict[str, Any]]]) -> Optional[PerformanceBottleneck]:
        """Detect I/O-related bottlenecks"""
        disk_read = metrics.get('disk_read_rate')
        disk_write = metrics.get('disk_write_rate')
        
        if not disk_read and not disk_write:
            return None
        
        # Check for high I/O activity
        high_io = False
        io_metrics = []
        
        if disk_read and disk_read.value > 100:  # > 100 MB/s
            high_io = True
            io_metrics.append(disk_read)
        
        if disk_write and disk_write.value > 100:  # > 100 MB/s
            high_io = True
            io_metrics.append(disk_write)
        
        if high_io:
            return PerformanceBottleneck(
                component='disk_io',
                issue_type='high_io',
                severity=Urgency.MEDIUM,
                description='High disk I/O activity detected',
                metrics=io_metrics,
                root_cause='Heavy disk operations or inefficient I/O patterns',
                recommendations=[
                    'Implement read/write caching',
                    'Optimize database queries',
                    'Use SSD storage if available',
                    'Implement asynchronous I/O operations',
                    'Batch small I/O operations'
                ]
            )
        
        return None
    
    def _detect_database_bottleneck(self, metrics: Dict[str, PerformanceMetric], 
                                   historical_data: Dict[str, List[Dict[str, Any]]]) -> Optional[PerformanceBottleneck]:
        """Detect database-related bottlenecks"""
        if 'avg_db_query_time' not in metrics:
            return None
        
        db_metric = metrics['avg_db_query_time']
        
        # Slow database queries
        if db_metric.value > 50:  # > 50ms average
            severity = Urgency.HIGH if db_metric.value > 100 else Urgency.MEDIUM
            
            return PerformanceBottleneck(
                component='database',
                issue_type='slow_queries',
                severity=severity,
                description=f'Average database query time is {db_metric.value:.1f}ms, which may impact performance',
                metrics=[db_metric],
                root_cause=self._determine_db_root_cause(db_metric.value),
                recommendations=[
                    'Add database indexes on frequently queried columns',
                    'Optimize slow queries using EXPLAIN plans',
                    'Implement query result caching',
                    'Consider database connection pooling',
                    'Review and optimize database schema',
                    'Consider read replicas for read-heavy workloads'
                ]
            )
        
        return None
    
    def _detect_network_bottleneck(self, metrics: Dict[str, PerformanceMetric], 
                                  historical_data: Dict[str, List[Dict[str, Any]]]) -> Optional[PerformanceBottleneck]:
        """Detect network-related bottlenecks"""
        # This would require more sophisticated network analysis
        # For now, implement basic detection
        
        if 'avg_response_time' not in metrics:
            return None
        
        response_time = metrics['avg_response_time']
        
        # High response times might indicate network issues
        if response_time.value > 1000:  # > 1 second
            return PerformanceBottleneck(
                component='network',
                issue_type='high_latency',
                severity=Urgency.HIGH,
                description=f'High response times ({response_time.value:.1f}ms) may indicate network bottlenecks',
                metrics=[response_time],
                root_cause='Network latency or bandwidth limitations',
                recommendations=[
                    'Implement CDN for static assets',
                    'Optimize payload sizes',
                    'Enable compression',
                    'Use persistent connections',
                    'Consider edge caching'
                ]
            )
        
        return None
    
    def _analyze_trend(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trend in historical data"""
        if len(data) < 2:
            return {'trend': 'insufficient_data'}
        
        values = [point['value'] for point in data[-10:]]  # Last 10 points
        
        if len(values) < 2:
            return {'trend': 'stable'}
        
        # Simple trend analysis
        first_half = values[:len(values)//2]
        second_half = values[len(values)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percent = ((second_avg - first_avg) / first_avg) * 100 if first_avg > 0 else 0
        
        if change_percent > 10:
            trend = 'increasing'
        elif change_percent < -10:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change_percent': change_percent,
            'current_avg': second_avg,
            'previous_avg': first_avg
        }
    
    def _determine_cpu_root_cause(self, cpu_usage: float, trend_analysis: Dict[str, Any]) -> str:
        """Determine root cause of CPU bottleneck"""
        if trend_analysis.get('trend') == 'increasing':
            return 'CPU usage is trending upward, possibly due to increasing load or inefficient algorithms'
        elif cpu_usage > 95:
            return 'CPU is at maximum capacity, likely due to CPU-bound operations or insufficient resources'
        else:
            return 'High CPU usage may be due to inefficient code, lack of caching, or resource-intensive operations'
    
    def _determine_memory_root_cause(self, memory_usage: float) -> str:
        """Determine root cause of memory bottleneck"""
        if memory_usage > 95:
            return 'Memory usage is critical, likely due to memory leaks or insufficient memory allocation'
        else:
            return 'High memory usage may be due to large data structures, memory leaks, or inefficient memory management'
    
    def _determine_db_root_cause(self, query_time: float) -> str:
        """Determine root cause of database bottleneck"""
        if query_time > 100:
            return 'Very slow queries indicate missing indexes, complex queries, or database server overload'
        else:
            return 'Slow queries may be due to missing indexes, inefficient query patterns, or suboptimal database configuration'
    
    def _load_detection_rules(self) -> Dict[str, Any]:
        """Load bottleneck detection rules"""
        return {
            'cpu_high_threshold': 85,
            'cpu_critical_threshold': 95,
            'memory_high_threshold': 80,
            'memory_critical_threshold': 95,
            'response_time_warning': 200,
            'response_time_critical': 1000,
            'db_query_warning': 50,
            'db_query_critical': 100
        }

class OptimizationEngine:
    """Generates optimization recommendations based on bottlenecks"""
    
    def __init__(self):
        self.optimization_rules = self._load_optimization_rules()
        self.best_practices = self._load_best_practices()
        
    def generate_recommendations(self, bottlenecks: List[PerformanceBottleneck], 
                               system_profile: SystemProfile, 
                               current_metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on bottlenecks"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            recs = self._generate_bottleneck_recommendations(bottleneck, system_profile, current_metrics)
            recommendations.extend(recs)
        
        # Add proactive optimizations
        proactive_recs = self._generate_proactive_recommendations(system_profile, current_metrics)
        recommendations.extend(proactive_recs)
        
        # Sort by impact and urgency
        recommendations.sort(key=lambda x: (x.urgency.value, x.impact_level.value), reverse=True)
        
        return recommendations
    
    def _generate_bottleneck_recommendations(self, bottleneck: PerformanceBottleneck, 
                                           system_profile: SystemProfile,
                                           metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate recommendations for specific bottleneck"""
        recommendations = []
        
        if bottleneck.component == 'cpu':
            recommendations.extend(self._generate_cpu_optimizations(bottleneck, system_profile, metrics))
        elif bottleneck.component == 'memory':
            recommendations.extend(self._generate_memory_optimizations(bottleneck, system_profile, metrics))
        elif bottleneck.component == 'disk_io':
            recommendations.extend(self._generate_io_optimizations(bottleneck, system_profile, metrics))
        elif bottleneck.component == 'database':
            recommendations.extend(self._generate_database_optimizations(bottleneck, system_profile, metrics))
        elif bottleneck.component == 'network':
            recommendations.extend(self._generate_network_optimizations(bottleneck, system_profile, metrics))
        
        return recommendations
    
    def _generate_cpu_optimizations(self, bottleneck: PerformanceBottleneck, 
                                   system_profile: SystemProfile,
                                   metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate CPU optimization recommendations"""
        recommendations = []
        
        # Caching recommendation
        recommendations.append(OptimizationRecommendation(
            id="cpu_caching_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Implement Application-Level Caching",
            description="Add caching layer to reduce CPU-intensive computations by storing frequently accessed results",
            optimization_type=OptimizationType.CACHING,
            urgency=bottleneck.severity,
            impact_level=ImpactLevel.HIGH,
            estimated_improvement={'cpu_usage': -30, 'response_time': -40},
            implementation_time=4,
            implementation_complexity="medium",
            code_changes_required=[
                {
                    "file_pattern": "*.py",
                    "change_type": "add_caching",
                    "description": "Add @lru_cache decorators or Redis caching"
                }
            ],
            configuration_changes={
                "redis": {"enabled": True, "max_memory": "256mb"},
                "cache_ttl": 3600
            },
            dependencies_needed=["redis", "python-redis"],
            rollback_plan="Remove cache configuration and revert to direct computation",
            success_metrics=["cpu_usage < 70%", "response_time < 200ms"],
            confidence_score=0.85
        ))
        
        # Algorithm optimization
        if 'python' in system_profile.technology_stack:
            recommendations.append(OptimizationRecommendation(
                id="cpu_algorithm_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
                title="Optimize CPU-Intensive Algorithms",
                description="Replace inefficient algorithms with optimized versions and use vectorized operations",
                optimization_type=OptimizationType.ALGORITHM,
                urgency=bottleneck.severity,
                impact_level=ImpactLevel.MEDIUM,
                estimated_improvement={'cpu_usage': -25, 'throughput': 20},
                implementation_time=8,
                implementation_complexity="high",
                code_changes_required=[
                    {
                        "file_pattern": "*.py",
                        "change_type": "optimize_algorithms",
                        "description": "Replace loops with numpy/pandas operations, optimize sorting algorithms"
                    }
                ],
                configuration_changes={},
                dependencies_needed=["numpy", "pandas"],
                rollback_plan="Keep backup of original algorithms and revert if needed",
                success_metrics=["cpu_usage < 60%", "algorithm_execution_time < 100ms"],
                confidence_score=0.75
            ))
        
        return recommendations
    
    def _generate_memory_optimizations(self, bottleneck: PerformanceBottleneck, 
                                     system_profile: SystemProfile,
                                     metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        # Memory pooling
        recommendations.append(OptimizationRecommendation(
            id="memory_pooling_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Implement Memory Pooling",
            description="Use memory pooling to reduce allocation overhead and memory fragmentation",
            optimization_type=OptimizationType.MEMORY,
            urgency=bottleneck.severity,
            impact_level=ImpactLevel.MEDIUM,
            estimated_improvement={'memory_usage': -20, 'gc_time': -30},
            implementation_time=6,
            implementation_complexity="medium",
            code_changes_required=[
                {
                    "file_pattern": "*.py",
                    "change_type": "add_memory_pools",
                    "description": "Implement object pools for frequently created/destroyed objects"
                }
            ],
            configuration_changes={
                "memory_pool_size": 1000,
                "pool_growth_factor": 1.5
            },
            dependencies_needed=[],
            rollback_plan="Disable memory pools and revert to standard allocation",
            success_metrics=["memory_usage < 70%", "allocation_rate < 1000/s"],
            confidence_score=0.8
        ))
        
        return recommendations
    
    def _generate_io_optimizations(self, bottleneck: PerformanceBottleneck, 
                                  system_profile: SystemProfile,
                                  metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate I/O optimization recommendations"""
        recommendations = []
        
        # Async I/O
        recommendations.append(OptimizationRecommendation(
            id="async_io_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Implement Asynchronous I/O Operations",
            description="Replace synchronous I/O with async operations to improve throughput",
            optimization_type=OptimizationType.DISK_IO,
            urgency=bottleneck.severity,
            impact_level=ImpactLevel.HIGH,
            estimated_improvement={'io_wait_time': -50, 'throughput': 40},
            implementation_time=12,
            implementation_complexity="high",
            code_changes_required=[
                {
                    "file_pattern": "*.py",
                    "change_type": "async_io_conversion",
                    "description": "Convert file operations to async/await pattern"
                }
            ],
            configuration_changes={
                "async_io_enabled": True,
                "io_thread_pool_size": 10
            },
            dependencies_needed=["aiofiles", "asyncio"],
            rollback_plan="Revert to synchronous I/O operations",
            success_metrics=["io_wait_time < 10ms", "concurrent_operations > 100"],
            confidence_score=0.8
        ))
        
        return recommendations
    
    def _generate_database_optimizations(self, bottleneck: PerformanceBottleneck, 
                                       system_profile: SystemProfile,
                                       metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate database optimization recommendations"""
        recommendations = []
        
        # Database indexing
        recommendations.append(OptimizationRecommendation(
            id="db_indexing_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Optimize Database Indexes",
            description="Add missing indexes and optimize existing ones based on query patterns",
            optimization_type=OptimizationType.DATABASE,
            urgency=bottleneck.severity,
            impact_level=ImpactLevel.HIGH,
            estimated_improvement={'query_time': -60, 'db_cpu': -40},
            implementation_time=3,
            implementation_complexity="low",
            code_changes_required=[
                {
                    "file_pattern": "*.sql",
                    "change_type": "add_indexes",
                    "description": "Add indexes on frequently queried columns"
                }
            ],
            configuration_changes={
                "index_maintenance": True,
                "auto_update_statistics": True
            },
            dependencies_needed=[],
            rollback_plan="Drop newly created indexes if performance degrades",
            success_metrics=["avg_query_time < 30ms", "slow_queries < 5%"],
            confidence_score=0.9
        ))
        
        # Connection pooling
        recommendations.append(OptimizationRecommendation(
            id="db_pooling_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Implement Database Connection Pooling",
            description="Use connection pooling to reduce connection overhead and improve scalability",
            optimization_type=OptimizationType.DATABASE,
            urgency=Urgency.MEDIUM,
            impact_level=ImpactLevel.MEDIUM,
            estimated_improvement={'connection_time': -70, 'concurrent_users': 50},
            implementation_time=2,
            implementation_complexity="low",
            code_changes_required=[
                {
                    "file_pattern": "database.py",
                    "change_type": "add_connection_pool",
                    "description": "Configure database connection pool"
                }
            ],
            configuration_changes={
                "pool_size": 10,
                "max_overflow": 5,
                "pool_timeout": 30
            },
            dependencies_needed=["sqlalchemy", "psycopg2-pool"],
            rollback_plan="Revert to direct database connections",
            success_metrics=["connection_time < 10ms", "pool_utilization < 80%"],
            confidence_score=0.95
        ))
        
        return recommendations
    
    def _generate_network_optimizations(self, bottleneck: PerformanceBottleneck, 
                                      system_profile: SystemProfile,
                                      metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate network optimization recommendations"""
        recommendations = []
        
        # Response compression
        recommendations.append(OptimizationRecommendation(
            id="compression_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Enable Response Compression",
            description="Implement gzip/brotli compression to reduce payload sizes and improve transfer speeds",
            optimization_type=OptimizationType.NETWORK,
            urgency=bottleneck.severity,
            impact_level=ImpactLevel.MEDIUM,
            estimated_improvement={'response_size': -70, 'transfer_time': -50},
            implementation_time=1,
            implementation_complexity="low",
            code_changes_required=[
                {
                    "file_pattern": "server.py",
                    "change_type": "enable_compression",
                    "description": "Add compression middleware"
                }
            ],
            configuration_changes={
                "compression_enabled": True,
                "compression_level": 6,
                "min_size": 1024
            },
            dependencies_needed=[],
            rollback_plan="Disable compression middleware",
            success_metrics=["response_size < 50KB", "transfer_time < 200ms"],
            confidence_score=0.95
        ))
        
        return recommendations
    
    def _generate_proactive_recommendations(self, system_profile: SystemProfile, 
                                          metrics: Dict[str, PerformanceMetric]) -> List[OptimizationRecommendation]:
        """Generate proactive optimization recommendations"""
        recommendations = []
        
        # Monitoring and alerting
        recommendations.append(OptimizationRecommendation(
            id="monitoring_" + hashlib.md5(str(time.time()).encode()).hexdigest()[:8],
            title="Implement Comprehensive Performance Monitoring",
            description="Set up monitoring and alerting for proactive performance management",
            optimization_type=OptimizationType.ARCHITECTURE,
            urgency=Urgency.LOW,
            impact_level=ImpactLevel.MEDIUM,
            estimated_improvement={'incident_response': 80, 'downtime': -60},
            implementation_time=4,
            implementation_complexity="medium",
            code_changes_required=[
                {
                    "file_pattern": "monitoring.py",
                    "change_type": "add_metrics",
                    "description": "Add custom metrics and health checks"
                }
            ],
            configuration_changes={
                "metrics_collection": True,
                "alert_thresholds": {"cpu": 80, "memory": 85, "response_time": 500}
            },
            dependencies_needed=["prometheus", "grafana", "alertmanager"],
            rollback_plan="Remove monitoring components if they impact performance",
            success_metrics=["monitoring_coverage > 90%", "alert_response_time < 5min"],
            confidence_score=0.85
        ))
        
        return recommendations
    
    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules and patterns"""
        return {
            "cpu_optimizations": {
                "caching": {"impact": 0.8, "complexity": "medium"},
                "algorithms": {"impact": 0.7, "complexity": "high"},
                "parallelization": {"impact": 0.9, "complexity": "high"}
            },
            "memory_optimizations": {
                "pooling": {"impact": 0.6, "complexity": "medium"},
                "gc_tuning": {"impact": 0.5, "complexity": "low"},
                "data_structures": {"impact": 0.7, "complexity": "medium"}
            },
            "io_optimizations": {
                "async_io": {"impact": 0.8, "complexity": "high"},
                "caching": {"impact": 0.7, "complexity": "medium"},
                "batching": {"impact": 0.6, "complexity": "medium"}
            }
        }
    
    def _load_best_practices(self) -> Dict[str, List[str]]:
        """Load performance best practices"""
        return {
            "general": [
                "Profile before optimizing",
                "Measure the impact of changes",
                "Optimize the bottleneck first",
                "Consider trade-offs between different resources"
            ],
            "cpu": [
                "Use appropriate data structures",
                "Minimize object creation in hot paths",
                "Use caching for expensive computations",
                "Consider parallelization for CPU-bound tasks"
            ],
            "memory": [
                "Avoid memory leaks",
                "Use memory profiling tools",
                "Implement proper garbage collection",
                "Use memory-efficient data structures"
            ],
            "io": [
                "Use asynchronous I/O when possible",
                "Implement proper error handling",
                "Batch small operations",
                "Use appropriate buffer sizes"
            ]
        }

class PerformanceOptimizationAdvisor:
    """Main advisor system that coordinates all optimization components"""
    
    def __init__(self):
        self.profiler = PerformanceProfiler()
        self.bottleneck_detector = BottleneckDetector()
        self.optimization_engine = OptimizationEngine()
        self.system_profiles: Dict[str, SystemProfile] = {}
        self.optimization_history: Dict[str, List[Dict[str, Any]]] = {}
        
    def analyze_performance(self, app_id: str, app_metrics: Dict[str, Any] = None, 
                          duration: int = 60) -> Dict[str, Any]:
        """Perform comprehensive performance analysis"""
        
        # Get system profile
        system_profile = self._get_system_profile(app_id)
        
        # Start profiling
        self.profiler.start_profiling(duration)
        
        # Wait for profiling to complete
        time.sleep(duration)
        
        # Get current metrics
        system_metrics = self.profiler.get_current_metrics()
        
        # Add application metrics if provided
        if app_metrics:
            app_perf_metrics = self.profiler.analyze_application_metrics(app_metrics)
            system_metrics.update(app_perf_metrics)
        
        # Detect bottlenecks
        bottlenecks = self.bottleneck_detector.detect_bottlenecks(
            system_metrics, 
            dict(self.profiler.metrics_history)
        )
        
        # Generate recommendations
        recommendations = self.optimization_engine.generate_recommendations(
            bottlenecks, 
            system_profile, 
            system_metrics
        )
        
        # Prepare analysis result
        analysis_result = {
            "app_id": app_id,
            "timestamp": time.time(),
            "analysis_duration": duration,
            "system_metrics": {name: asdict(metric) for name, metric in system_metrics.items()},
            "bottlenecks": [asdict(bottleneck) for bottleneck in bottlenecks],
            "recommendations": [asdict(rec) for rec in recommendations],
            "overall_health_score": self._calculate_health_score(system_metrics, bottlenecks),
            "summary": self._generate_analysis_summary(system_metrics, bottlenecks, recommendations)
        }
        
        # Store in history
        self._store_analysis_history(app_id, analysis_result)
        
        return analysis_result
    
    def get_quick_assessment(self, app_id: str, app_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get quick performance assessment without extended profiling"""
        
        # Get current metrics
        system_metrics = self.profiler.get_current_metrics()
        
        # Add application metrics if provided
        if app_metrics:
            app_perf_metrics = self.profiler.analyze_application_metrics(app_metrics)
            system_metrics.update(app_perf_metrics)
        
        # Quick bottleneck detection
        bottlenecks = self.bottleneck_detector.detect_bottlenecks(system_metrics, {})
        
        # Health score
        health_score = self._calculate_health_score(system_metrics, bottlenecks)
        
        # Quick recommendations (top 3)
        system_profile = self._get_system_profile(app_id)
        all_recommendations = self.optimization_engine.generate_recommendations(
            bottlenecks, system_profile, system_metrics
        )
        quick_recommendations = all_recommendations[:3]
        
        return {
            "app_id": app_id,
            "timestamp": time.time(),
            "health_score": health_score,
            "critical_issues": len([b for b in bottlenecks if b.severity == Urgency.CRITICAL]),
            "top_recommendations": [asdict(rec) for rec in quick_recommendations],
            "metrics_snapshot": {name: metric.value for name, metric in system_metrics.items()},
            "assessment_type": "quick"
        }
    
    def track_optimization_impact(self, app_id: str, optimization_id: str, 
                                before_metrics: Dict[str, Any], 
                                after_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Track the impact of applied optimizations"""
        
        impact_analysis = {}
        
        for metric_name in before_metrics:
            if metric_name in after_metrics:
                before_val = before_metrics[metric_name]
                after_val = after_metrics[metric_name]
                
                if isinstance(before_val, (int, float)) and isinstance(after_val, (int, float)):
                    if before_val != 0:
                        change_percent = ((after_val - before_val) / before_val) * 100
                    else:
                        change_percent = 0
                    
                    impact_analysis[metric_name] = {
                        "before": before_val,
                        "after": after_val,
                        "change_percent": change_percent,
                        "improvement": change_percent < 0 if metric_name in ['cpu_usage', 'memory_usage', 'response_time'] else change_percent > 0
                    }
        
        # Calculate overall impact score
        improvement_metrics = [v for v in impact_analysis.values() if v.get('improvement', False)]
        overall_impact = len(improvement_metrics) / len(impact_analysis) if impact_analysis else 0
        
        impact_result = {
            "optimization_id": optimization_id,
            "app_id": app_id,
            "timestamp": time.time(),
            "impact_analysis": impact_analysis,
            "overall_impact_score": overall_impact,
            "success": overall_impact > 0.5,
            "summary": self._generate_impact_summary(impact_analysis)
        }
        
        # Store impact tracking
        if app_id not in self.optimization_history:
            self.optimization_history[app_id] = []
        self.optimization_history[app_id].append(impact_result)
        
        return impact_result
    
    def get_optimization_history(self, app_id: str) -> Dict[str, Any]:
        """Get optimization history and trends for an application"""
        if app_id not in self.optimization_history:
            return {"message": "No optimization history found"}
        
        history = self.optimization_history[app_id]
        
        # Calculate success rate
        successful_optimizations = sum(1 for opt in history if opt.get('success', False))
        success_rate = successful_optimizations / len(history) if history else 0
        
        # Most effective optimization types
        type_effectiveness = defaultdict(list)
        for opt in history:
            opt_type = opt.get('optimization_type', 'unknown')
            impact_score = opt.get('overall_impact_score', 0)
            type_effectiveness[opt_type].append(impact_score)
        
        avg_effectiveness = {
            opt_type: statistics.mean(scores) 
            for opt_type, scores in type_effectiveness.items()
        }
        
        return {
            "app_id": app_id,
            "total_optimizations": len(history),
            "success_rate": success_rate,
            "average_impact_score": statistics.mean([h.get('overall_impact_score', 0) for h in history]),
            "most_effective_types": sorted(avg_effectiveness.items(), key=lambda x: x[1], reverse=True)[:5],
            "recent_optimizations": history[-5:],  # Last 5
            "trends": self._analyze_optimization_trends(history)
        }
    
    def _get_system_profile(self, app_id: str) -> SystemProfile:
        """Get or create system profile for application"""
        if app_id not in self.system_profiles:
            # Create default profile - in production, this would be configured
            self.system_profiles[app_id] = SystemProfile(
                cpu_cores=psutil.cpu_count(),
                memory_gb=psutil.virtual_memory().total / (1024**3),
                disk_type="SSD",  # Assumption
                network_bandwidth="1Gbps",  # Assumption
                application_type="web_service",
                technology_stack=["python", "flask", "postgresql"],
                deployment_environment="cloud",
                expected_load={"concurrent_users": 100, "requests_per_second": 50}
            )
        
        return self.system_profiles[app_id]
    
    def _calculate_health_score(self, metrics: Dict[str, PerformanceMetric], 
                              bottlenecks: List[PerformanceBottleneck]) -> float:
        """Calculate overall system health score (0-100)"""
        score = 100.0
        
        # Deduct points for high resource usage
        if 'cpu_usage' in metrics:
            cpu_usage = metrics['cpu_usage'].value
            if cpu_usage > 80:
                score -= (cpu_usage - 80) * 2  # 2 points per % over 80%
        
        if 'memory_usage' in metrics:
            memory_usage = metrics['memory_usage'].value
            if memory_usage > 75:
                score -= (memory_usage - 75) * 1.5  # 1.5 points per % over 75%
        
        if 'avg_response_time' in metrics:
            response_time = metrics['avg_response_time'].value
            if response_time > 200:
                score -= min(30, (response_time - 200) / 20)  # Up to 30 points for response time
        
        # Deduct points for bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.severity == Urgency.CRITICAL:
                score -= 25
            elif bottleneck.severity == Urgency.HIGH:
                score -= 15
            elif bottleneck.severity == Urgency.MEDIUM:
                score -= 8
        
        return max(0, min(100, score))
    
    def _generate_analysis_summary(self, metrics: Dict[str, PerformanceMetric], 
                                 bottlenecks: List[PerformanceBottleneck], 
                                 recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Generate human-readable analysis summary"""
        
        critical_bottlenecks = [b for b in bottlenecks if b.severity == Urgency.CRITICAL]
        high_impact_recommendations = [r for r in recommendations if r.impact_level in [ImpactLevel.HIGH, ImpactLevel.TRANSFORMATIVE]]
        
        summary = {
            "status": "critical" if critical_bottlenecks else "warning" if bottlenecks else "healthy",
            "key_findings": [],
            "priority_actions": [],
            "estimated_improvement": {}
        }
        
        # Key findings
        if critical_bottlenecks:
            summary["key_findings"].append(f"Found {len(critical_bottlenecks)} critical performance issue(s)")
        
        if 'cpu_usage' in metrics and metrics['cpu_usage'].value > 80:
            summary["key_findings"].append(f"High CPU usage at {metrics['cpu_usage'].value:.1f}%")
        
        if 'memory_usage' in metrics and metrics['memory_usage'].value > 80:
            summary["key_findings"].append(f"High memory usage at {metrics['memory_usage'].value:.1f}%")
        
        # Priority actions
        for rec in high_impact_recommendations[:3]:
            summary["priority_actions"].append(rec.title)
        
        # Estimated improvement
        if recommendations:
            cpu_improvement = sum(r.estimated_improvement.get('cpu_usage', 0) for r in recommendations[:3])
            memory_improvement = sum(r.estimated_improvement.get('memory_usage', 0) for r in recommendations[:3])
            response_improvement = sum(r.estimated_improvement.get('response_time', 0) for r in recommendations[:3])
            
            summary["estimated_improvement"] = {
                "cpu_usage": f"{abs(cpu_improvement):.0f}% reduction" if cpu_improvement < 0 else "No significant change",
                "memory_usage": f"{abs(memory_improvement):.0f}% reduction" if memory_improvement < 0 else "No significant change",
                "response_time": f"{abs(response_improvement):.0f}% improvement" if response_improvement < 0 else "No significant change"
            }
        
        return summary
    
    def _generate_impact_summary(self, impact_analysis: Dict[str, Any]) -> str:
        """Generate human-readable impact summary"""
        improvements = []
        regressions = []
        
        for metric_name, analysis in impact_analysis.items():
            if analysis.get('improvement', False):
                improvements.append(f"{metric_name}: {abs(analysis['change_percent']):.1f}% improvement")
            elif analysis['change_percent'] != 0:
                regressions.append(f"{metric_name}: {abs(analysis['change_percent']):.1f}% regression")
        
        if improvements and not regressions:
            return f"Optimization successful: {', '.join(improvements)}"
        elif improvements and regressions:
            return f"Mixed results: {', '.join(improvements[:2])} but {', '.join(regressions[:1])}"
        elif regressions:
            return f"Optimization had negative impact: {', '.join(regressions[:2])}"
        else:
            return "No significant impact detected"
    
    def _analyze_optimization_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in optimization history"""
        if len(history) < 3:
            return {"message": "Insufficient data for trend analysis"}
        
        recent_scores = [h.get('overall_impact_score', 0) for h in history[-5:]]
        earlier_scores = [h.get('overall_impact_score', 0) for h in history[-10:-5]] if len(history) >= 10 else []
        
        trends = {"improving": False, "declining": False, "stable": False}
        
        if earlier_scores:
            recent_avg = statistics.mean(recent_scores)
            earlier_avg = statistics.mean(earlier_scores)
            
            if recent_avg > earlier_avg + 0.1:
                trends["improving"] = True
            elif recent_avg < earlier_avg - 0.1:
                trends["declining"] = True
            else:
                trends["stable"] = True
        
        return {
            "trends": trends,
            "recent_average_impact": statistics.mean(recent_scores),
            "success_rate_trend": "increasing" if trends["improving"] else "decreasing" if trends["declining"] else "stable"
        }
    
    def _store_analysis_history(self, app_id: str, analysis_result: Dict[str, Any]):
        """Store analysis in history"""
        # In production, this would be stored in a database
        pass

if __name__ == "__main__":
    # Example usage
    advisor = PerformanceOptimizationAdvisor()
    
    # Example application metrics
    app_metrics = {
        "response_times": [150, 200, 180, 300, 250],
        "requests_per_second": 45,
        "error_rate": 0.02,
        "db_query_times": [25, 30, 45, 60, 35]
    }
    
    # Quick assessment
    quick_assessment = advisor.get_quick_assessment("my_app", app_metrics)
    print("Quick Assessment:")
    print(json.dumps(quick_assessment, indent=2, default=str))
    
    # Full analysis (shortened for demo)
    # full_analysis = advisor.analyze_performance("my_app", app_metrics, duration=10)
    # print("\nFull Analysis:")
    # print(json.dumps(full_analysis, indent=2, default=str))