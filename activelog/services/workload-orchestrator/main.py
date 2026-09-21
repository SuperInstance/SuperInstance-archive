#!/usr/bin/env python3
"""
Workload Orchestrator - Streamlines system for various workload scenarios
Dynamically adjusts resource allocation, service priorities, and system configuration
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiohttp
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import psutil
import docker
import yaml
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Workload Orchestrator", version="1.0.0")

class WorkloadType(str, Enum):
    FINANCIAL_TRADING = "financial_trading"
    ANALYTICS_HEAVY = "analytics_heavy"
    WEB_TRAFFIC = "web_traffic"
    BATCH_PROCESSING = "batch_processing"
    DEVELOPMENT = "development"
    TESTING = "testing"
    MINIMAL = "minimal"

class WorkloadProfile(BaseModel):
    profile_name: str
    workload_type: WorkloadType
    resource_allocation: Dict[str, Any]
    service_priorities: Dict[str, int]
    scaling_rules: Dict[str, Any]
    performance_targets: Dict[str, float]

class ResourceRequest(BaseModel):
    service_name: str
    cpu_request: Optional[float] = None
    memory_request: Optional[int] = None
    priority: Optional[int] = None

class ScalingDecision(BaseModel):
    service_name: str
    action: str  # scale_up, scale_down, migrate, optimize
    current_instances: int
    target_instances: int
    reason: str

class WorkloadOrchestrator:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "workload_orchestrator.db"
        self.config_path = Path(__file__).parent / "config"
        self.profiles_path = self.config_path / "profiles"
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.config_path.mkdir(exist_ok=True)
        self.profiles_path.mkdir(exist_ok=True)
        
        self._init_database()
        self._init_docker_client()
        self._load_workload_profiles()
        
        # Current system state
        self.current_workload = WorkloadType.DEVELOPMENT
        self.active_profile = None
        self.resource_usage = {}
        self.service_metrics = {}
        
    def _init_database(self):
        """Initialize SQLite database for workload data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workload_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT UNIQUE NOT NULL,
                    workload_type TEXT NOT NULL,
                    resource_allocation JSON NOT NULL,
                    service_priorities JSON NOT NULL,
                    scaling_rules JSON NOT NULL,
                    performance_targets JSON NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS workload_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_workload TEXT,
                    to_workload TEXT NOT NULL,
                    transition_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER,
                    resource_changes JSON,
                    success BOOLEAN,
                    error_message TEXT
                );
                
                CREATE TABLE IF NOT EXISTS resource_allocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    workload_type TEXT NOT NULL,
                    cpu_allocated REAL,
                    memory_allocated INTEGER,
                    instances_count INTEGER,
                    priority INTEGER
                );
                
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    workload_type TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    target_value REAL,
                    status TEXT
                );
                
                CREATE TABLE IF NOT EXISTS scaling_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    from_instances INTEGER,
                    to_instances INTEGER,
                    reason TEXT,
                    workload_context TEXT,
                    executed BOOLEAN DEFAULT FALSE,
                    execution_result TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_workload_transitions_time ON workload_transitions(transition_time);
                CREATE INDEX IF NOT EXISTS idx_performance_metrics_time ON performance_metrics(timestamp);
            """)
            
    def _init_docker_client(self):
        """Initialize Docker client for container management"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
            
    def _load_workload_profiles(self):
        """Load and initialize workload profiles"""
        self.workload_profiles = {
            WorkloadType.FINANCIAL_TRADING: {
                'profile_name': 'FinancialTrading',
                'resource_allocation': {
                    'trading-engine': {'cpu': 4.0, 'memory': 8192, 'priority': 1, 'instances': 3},
                    'settlement-engine': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 2},
                    'compliance-engine': {'cpu': 1.0, 'memory': 2048, 'priority': 2, 'instances': 2},
                    'market-data': {'cpu': 2.0, 'memory': 4096, 'priority': 1, 'instances': 2},
                    'wallet-service': {'cpu': 1.0, 'memory': 2048, 'priority': 3, 'instances': 1},
                    'dream-mode': {'cpu': 0.5, 'memory': 1024, 'priority': 4, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 70,
                    'memory_threshold': 80,
                    'response_time_threshold': 100,
                    'scale_up_cooldown': 300,
                    'scale_down_cooldown': 600
                },
                'performance_targets': {
                    'avg_response_time': 50.0,
                    'p95_response_time': 200.0,
                    'error_rate': 0.1,
                    'throughput_tps': 1000.0
                }
            },
            
            WorkloadType.ANALYTICS_HEAVY: {
                'profile_name': 'AnalyticsHeavy',
                'resource_allocation': {
                    'analytics': {'cpu': 6.0, 'memory': 12288, 'priority': 1, 'instances': 4},
                    'data-orchestrator': {'cpu': 4.0, 'memory': 8192, 'priority': 1, 'instances': 2},
                    'reporting': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 2},
                    'ml-pipeline': {'cpu': 8.0, 'memory': 16384, 'priority': 1, 'instances': 2},
                    'observability-stack': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 1},
                    'trading-engine': {'cpu': 1.0, 'memory': 2048, 'priority': 3, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 80,
                    'memory_threshold': 85,
                    'queue_length_threshold': 100,
                    'scale_up_cooldown': 180,
                    'scale_down_cooldown': 900
                },
                'performance_targets': {
                    'job_completion_time': 300.0,
                    'queue_processing_rate': 50.0,
                    'data_throughput_mbps': 100.0,
                    'error_rate': 0.5
                }
            },
            
            WorkloadType.WEB_TRAFFIC: {
                'profile_name': 'WebTrafficOptimized',
                'resource_allocation': {
                    'api-gateway': {'cpu': 4.0, 'memory': 4096, 'priority': 1, 'instances': 5},
                    'frontend': {'cpu': 2.0, 'memory': 2048, 'priority': 1, 'instances': 4},
                    'user-management': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 3},
                    'content-delivery': {'cpu': 1.0, 'memory': 2048, 'priority': 2, 'instances': 3},
                    'cache-service': {'cpu': 2.0, 'memory': 4096, 'priority': 1, 'instances': 2},
                    'analytics': {'cpu': 1.0, 'memory': 2048, 'priority': 4, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 65,
                    'memory_threshold': 75,
                    'connection_threshold': 1000,
                    'scale_up_cooldown': 120,
                    'scale_down_cooldown': 300
                },
                'performance_targets': {
                    'avg_response_time': 100.0,
                    'p95_response_time': 500.0,
                    'concurrent_users': 5000.0,
                    'error_rate': 0.2
                }
            },
            
            WorkloadType.BATCH_PROCESSING: {
                'profile_name': 'BatchProcessing',
                'resource_allocation': {
                    'batch-processor': {'cpu': 8.0, 'memory': 16384, 'priority': 1, 'instances': 3},
                    'data-pipeline': {'cpu': 6.0, 'memory': 12288, 'priority': 1, 'instances': 2},
                    'file-processor': {'cpu': 4.0, 'memory': 8192, 'priority': 2, 'instances': 4},
                    'backup-dr': {'cpu': 2.0, 'memory': 4096, 'priority': 3, 'instances': 1},
                    'data-export': {'cpu': 2.0, 'memory': 4096, 'priority': 3, 'instances': 1},
                    'frontend': {'cpu': 0.5, 'memory': 1024, 'priority': 5, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 90,
                    'memory_threshold': 90,
                    'queue_depth_threshold': 500,
                    'scale_up_cooldown': 60,
                    'scale_down_cooldown': 1800
                },
                'performance_targets': {
                    'batch_completion_time': 1800.0,
                    'throughput_jobs_per_hour': 100.0,
                    'resource_efficiency': 85.0,
                    'error_rate': 1.0
                }
            },
            
            WorkloadType.DEVELOPMENT: {
                'profile_name': 'Development',
                'resource_allocation': {
                    'dev-productivity': {'cpu': 2.0, 'memory': 4096, 'priority': 1, 'instances': 1},
                    'api-gateway': {'cpu': 1.0, 'memory': 2048, 'priority': 2, 'instances': 1},
                    'frontend': {'cpu': 1.0, 'memory': 2048, 'priority': 2, 'instances': 1},
                    'trading-engine': {'cpu': 0.5, 'memory': 1024, 'priority': 3, 'instances': 1},
                    'observability-stack': {'cpu': 1.0, 'memory': 2048, 'priority': 2, 'instances': 1},
                    'backup-dr': {'cpu': 0.5, 'memory': 1024, 'priority': 4, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 85,
                    'memory_threshold': 85,
                    'scale_up_cooldown': 600,
                    'scale_down_cooldown': 300,
                    'enable_auto_scaling': False
                },
                'performance_targets': {
                    'build_time': 120.0,
                    'test_execution_time': 60.0,
                    'ide_response_time': 50.0,
                    'error_rate': 5.0
                }
            },
            
            WorkloadType.TESTING: {
                'profile_name': 'Testing',
                'resource_allocation': {
                    'test-runner': {'cpu': 4.0, 'memory': 8192, 'priority': 1, 'instances': 2},
                    'test-data-generator': {'cpu': 2.0, 'memory': 4096, 'priority': 1, 'instances': 1},
                    'performance-tester': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 1},
                    'api-gateway': {'cpu': 1.0, 'memory': 2048, 'priority': 3, 'instances': 1},
                    'observability-stack': {'cpu': 2.0, 'memory': 4096, 'priority': 2, 'instances': 1},
                    'all-services': {'cpu': 0.25, 'memory': 512, 'priority': 4, 'instances': 1}
                },
                'scaling_rules': {
                    'cpu_threshold': 95,
                    'memory_threshold': 95,
                    'test_queue_threshold': 50,
                    'scale_up_cooldown': 30,
                    'scale_down_cooldown': 600
                },
                'performance_targets': {
                    'test_execution_time': 300.0,
                    'test_success_rate': 98.0,
                    'coverage_percentage': 80.0,
                    'parallel_test_capacity': 20.0
                }
            },
            
            WorkloadType.MINIMAL: {
                'profile_name': 'Minimal',
                'resource_allocation': {
                    'api-gateway': {'cpu': 0.5, 'memory': 1024, 'priority': 1, 'instances': 1},
                    'essential-services': {'cpu': 0.5, 'memory': 1024, 'priority': 1, 'instances': 1},
                    'observability-stack': {'cpu': 0.25, 'memory': 512, 'priority': 2, 'instances': 1}
                },
                'scaling_rules': {
                    'enable_auto_scaling': False,
                    'cpu_threshold': 95,
                    'memory_threshold': 95
                },
                'performance_targets': {
                    'basic_functionality': True,
                    'response_time': 1000.0,
                    'resource_usage': 10.0
                }
            }
        }
        
        # Store profiles in database
        self._store_profiles()
        
    def _store_profiles(self):
        """Store workload profiles in database"""
        with sqlite3.connect(self.db_path) as conn:
            for workload_type, profile in self.workload_profiles.items():
                conn.execute("""
                    INSERT OR REPLACE INTO workload_profiles 
                    (profile_name, workload_type, resource_allocation, service_priorities, scaling_rules, performance_targets)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    profile['profile_name'],
                    workload_type.value,
                    json.dumps(profile['resource_allocation']),
                    json.dumps({k: v.get('priority', 3) for k, v in profile['resource_allocation'].items()}),
                    json.dumps(profile['scaling_rules']),
                    json.dumps(profile['performance_targets'])
                ))
                
    async def transition_workload(self, target_workload: WorkloadType, force: bool = False) -> Dict[str, Any]:
        """Transition system to a different workload profile"""
        start_time = datetime.now()
        
        if target_workload == self.current_workload and not force:
            return {
                'success': True,
                'message': f'Already running {target_workload.value} workload',
                'duration': 0
            }
            
        logger.info(f"Transitioning from {self.current_workload.value} to {target_workload.value}")
        
        try:
            # Get target profile
            target_profile = self.workload_profiles[target_workload]
            
            # Record transition start
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO workload_transitions (from_workload, to_workload, success)
                    VALUES (?, ?, FALSE)
                """, (self.current_workload.value, target_workload.value))
                transition_id = conn.lastrowid
                
            # Execute transition steps
            transition_steps = []
            
            # Step 1: Scale down non-priority services
            step_result = await self._scale_down_non_priority_services(target_profile)
            transition_steps.append(('scale_down', step_result))
            
            # Step 2: Reconfigure resource allocations
            step_result = await self._reconfigure_resources(target_profile)
            transition_steps.append(('reconfigure', step_result))
            
            # Step 3: Scale up priority services
            step_result = await self._scale_up_priority_services(target_profile)
            transition_steps.append(('scale_up', step_result))
            
            # Step 4: Update monitoring and alerting
            step_result = await self._update_monitoring_config(target_profile)
            transition_steps.append(('monitoring', step_result))
            
            # Step 5: Validate transition
            step_result = await self._validate_workload_transition(target_profile)
            transition_steps.append(('validation', step_result))
            
            # Update current workload
            self.current_workload = target_workload
            self.active_profile = target_profile
            
            # Record successful transition
            duration = (datetime.now() - start_time).total_seconds()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE workload_transitions 
                    SET success = TRUE, duration_seconds = ?, resource_changes = ?
                    WHERE id = ?
                """, (duration, json.dumps(transition_steps), transition_id))
                
            logger.info(f"Workload transition completed in {duration:.2f} seconds")
            
            return {
                'success': True,
                'from_workload': self.current_workload.value,
                'to_workload': target_workload.value,
                'duration': duration,
                'steps': transition_steps
            }
            
        except Exception as e:
            logger.error(f"Workload transition failed: {e}")
            
            # Record failed transition
            duration = (datetime.now() - start_time).total_seconds()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE workload_transitions 
                    SET success = FALSE, duration_seconds = ?, error_message = ?
                    WHERE id = ?
                """, (duration, str(e), transition_id))
                
            return {
                'success': False,
                'error': str(e),
                'duration': duration
            }
            
    async def _scale_down_non_priority_services(self, target_profile: Dict) -> Dict[str, Any]:
        """Scale down services not prioritized in target workload"""
        results = []
        target_services = set(target_profile['resource_allocation'].keys())
        
        # Get current running services
        current_services = await self._get_running_services()
        
        for service_name in current_services:
            if service_name not in target_services:
                # Service not needed in target workload - scale to minimal or stop
                result = await self._scale_service(service_name, 0)
                results.append({'service': service_name, 'action': 'stop', 'result': result})
            else:
                # Service needed but might need scaling down first
                current_instances = await self._get_service_instance_count(service_name)
                target_instances = target_profile['resource_allocation'][service_name]['instances']
                
                if current_instances > target_instances:
                    result = await self._scale_service(service_name, target_instances)
                    results.append({'service': service_name, 'action': 'scale_down', 'result': result})
                    
        return {'scaled_services': results, 'success': True}
        
    async def _reconfigure_resources(self, target_profile: Dict) -> Dict[str, Any]:
        """Reconfigure resource allocations for services"""
        results = []
        
        for service_name, allocation in target_profile['resource_allocation'].items():
            try:
                # Update CPU and memory limits
                if self.docker_client:
                    containers = self.docker_client.containers.list(
                        filters={'label': f'service={service_name}'}
                    )
                    
                    for container in containers:
                        # Update container resource constraints
                        cpu_limit = int(allocation['cpu'] * 1000000000)  # Convert to nanocpus
                        memory_limit = allocation['memory'] * 1024 * 1024  # Convert to bytes
                        
                        container.update(
                            cpu_quota=cpu_limit,
                            mem_limit=memory_limit
                        )
                        
                results.append({
                    'service': service_name,
                    'cpu_allocated': allocation['cpu'],
                    'memory_allocated': allocation['memory'],
                    'priority': allocation['priority'],
                    'success': True
                })
                
                # Store allocation in database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO resource_allocations 
                        (service_name, workload_type, cpu_allocated, memory_allocated, instances_count, priority)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        service_name,
                        self.current_workload.value,
                        allocation['cpu'],
                        allocation['memory'],
                        allocation['instances'],
                        allocation['priority']
                    ))
                    
            except Exception as e:
                logger.error(f"Failed to reconfigure {service_name}: {e}")
                results.append({'service': service_name, 'error': str(e), 'success': False})
                
        return {'configured_services': results, 'success': True}
        
    async def _scale_up_priority_services(self, target_profile: Dict) -> Dict[str, Any]:
        """Scale up high-priority services for target workload"""
        results = []
        
        # Sort services by priority (lower number = higher priority)
        services_by_priority = sorted(
            target_profile['resource_allocation'].items(),
            key=lambda x: x[1]['priority']
        )
        
        for service_name, allocation in services_by_priority:
            try:
                target_instances = allocation['instances']
                current_instances = await self._get_service_instance_count(service_name)
                
                if current_instances < target_instances:
                    result = await self._scale_service(service_name, target_instances)
                    results.append({
                        'service': service_name,
                        'from_instances': current_instances,
                        'to_instances': target_instances,
                        'priority': allocation['priority'],
                        'success': result
                    })
                    
                    # Wait briefly between scaling operations
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Failed to scale up {service_name}: {e}")
                results.append({'service': service_name, 'error': str(e), 'success': False})
                
        return {'scaled_services': results, 'success': True}
        
    async def _update_monitoring_config(self, target_profile: Dict) -> Dict[str, Any]:
        """Update monitoring and alerting configuration"""
        try:
            # Update observability stack with new thresholds
            config_update = {
                'workload_type': self.current_workload.value,
                'scaling_rules': target_profile['scaling_rules'],
                'performance_targets': target_profile['performance_targets'],
                'high_priority_services': [
                    service for service, config in target_profile['resource_allocation'].items()
                    if config['priority'] <= 2
                ]
            }
            
            # Send configuration to observability service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'http://localhost:8600/config/workload',
                    json=config_update
                ) as response:
                    if response.status == 200:
                        return {'monitoring_updated': True, 'success': True}
                    else:
                        return {'monitoring_updated': False, 'error': await response.text(), 'success': False}
                        
        except Exception as e:
            logger.warning(f"Failed to update monitoring config: {e}")
            return {'monitoring_updated': False, 'error': str(e), 'success': False}
            
    async def _validate_workload_transition(self, target_profile: Dict) -> Dict[str, Any]:
        """Validate that workload transition was successful"""
        validation_results = {
            'service_health': {},
            'resource_allocation': {},
            'performance_targets': {},
            'overall_success': True
        }
        
        # Check service health
        for service_name in target_profile['resource_allocation'].keys():
            try:
                health = await self._check_service_health(service_name)
                validation_results['service_health'][service_name] = health
                if not health:
                    validation_results['overall_success'] = False
            except Exception as e:
                validation_results['service_health'][service_name] = False
                validation_results['overall_success'] = False
                
        # Check resource allocations
        for service_name, expected_allocation in target_profile['resource_allocation'].items():
            try:
                actual_allocation = await self._get_service_resource_usage(service_name)
                validation_results['resource_allocation'][service_name] = {
                    'expected': expected_allocation,
                    'actual': actual_allocation,
                    'within_limits': self._validate_resource_allocation(expected_allocation, actual_allocation)
                }
            except Exception as e:
                validation_results['resource_allocation'][service_name] = {'error': str(e)}
                
        return validation_results
        
    async def _get_running_services(self) -> List[str]:
        """Get list of currently running services"""
        if not self.docker_client:
            return []
            
        try:
            containers = self.docker_client.containers.list(filters={'status': 'running'})
            services = []
            for container in containers:
                service_label = container.labels.get('service')
                if service_label:
                    services.append(service_label)
            return services
        except Exception as e:
            logger.error(f"Failed to get running services: {e}")
            return []
            
    async def _get_service_instance_count(self, service_name: str) -> int:
        """Get current instance count for a service"""
        if not self.docker_client:
            return 1
            
        try:
            containers = self.docker_client.containers.list(
                filters={'label': f'service={service_name}', 'status': 'running'}
            )
            return len(containers)
        except Exception as e:
            logger.error(f"Failed to get instance count for {service_name}: {e}")
            return 0
            
    async def _scale_service(self, service_name: str, target_instances: int) -> bool:
        """Scale a service to target instance count"""
        try:
            # This is a simplified implementation
            # In a real environment, this would integrate with Docker Swarm, Kubernetes, etc.
            logger.info(f"Scaling {service_name} to {target_instances} instances")
            
            if target_instances == 0:
                # Stop service
                if self.docker_client:
                    containers = self.docker_client.containers.list(
                        filters={'label': f'service={service_name}'}
                    )
                    for container in containers:
                        container.stop()
                        
            return True
        except Exception as e:
            logger.error(f"Failed to scale {service_name}: {e}")
            return False
            
    async def _check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        try:
            # Try to reach service health endpoint
            port_map = {
                'trading-engine': 8400,
                'settlement-engine': 8401,
                'compliance-engine': 8402,
                'market-data': 8403,
                'wallet-service': 8404,
                'dream-mode': 8405,
                'api-gateway': 8000,
                'observability-stack': 8600
            }
            
            port = port_map.get(service_name, 8000)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{port}/health', timeout=5) as response:
                    return response.status == 200
                    
        except Exception:
            return False
            
    async def _get_service_resource_usage(self, service_name: str) -> Dict[str, Any]:
        """Get current resource usage for a service"""
        try:
            if not self.docker_client:
                return {}
                
            containers = self.docker_client.containers.list(
                filters={'label': f'service={service_name}'}
            )
            
            if not containers:
                return {}
                
            # Get stats from first container (simplified)
            container = containers[0]
            stats = container.stats(stream=False)
            
            # Calculate CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
                          
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
            
            # Get memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            return {
                'cpu_percent': cpu_percent,
                'memory_usage_mb': memory_usage / (1024 * 1024),
                'memory_limit_mb': memory_limit / (1024 * 1024),
                'instance_count': len(containers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource usage for {service_name}: {e}")
            return {}
            
    def _validate_resource_allocation(self, expected: Dict, actual: Dict) -> bool:
        """Validate that actual resource usage is within expected limits"""
        if not actual:
            return False
            
        # Allow 20% tolerance
        tolerance = 0.2
        
        expected_cpu = expected.get('cpu', 1.0)
        actual_cpu = actual.get('cpu_percent', 0) / 100.0
        
        expected_memory = expected.get('memory', 1024)
        actual_memory = actual.get('memory_usage_mb', 0)
        
        cpu_ok = actual_cpu <= expected_cpu * (1 + tolerance)
        memory_ok = actual_memory <= expected_memory * (1 + tolerance)
        
        return cpu_ok and memory_ok
        
    async def auto_detect_workload(self) -> WorkloadType:
        """Automatically detect optimal workload based on system metrics"""
        try:
            # Collect system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory_usage = psutil.virtual_memory().percent
            
            # Get service-specific metrics
            service_metrics = {}
            active_services = await self._get_running_services()
            
            for service in active_services:
                usage = await self._get_service_resource_usage(service)
                if usage:
                    service_metrics[service] = usage
                    
            # Analyze patterns
            financial_services = ['trading-engine', 'settlement-engine', 'compliance-engine']
            analytics_services = ['analytics', 'ml-pipeline', 'data-orchestrator']
            web_services = ['api-gateway', 'frontend', 'user-management']
            
            financial_active = sum(1 for s in financial_services if s in active_services)
            analytics_active = sum(1 for s in analytics_services if s in active_services)
            web_active = sum(1 for s in web_services if s in active_services)
            
            # Decision logic
            if financial_active >= 2 and cpu_usage > 50:
                return WorkloadType.FINANCIAL_TRADING
            elif analytics_active >= 2 or any(s.startswith('ml-') for s in active_services):
                return WorkloadType.ANALYTICS_HEAVY
            elif web_active >= 2 and len(active_services) > 5:
                return WorkloadType.WEB_TRAFFIC
            elif cpu_usage < 30 and memory_usage < 50:
                return WorkloadType.MINIMAL
            else:
                return WorkloadType.DEVELOPMENT
                
        except Exception as e:
            logger.error(f"Auto-detection failed: {e}")
            return WorkloadType.DEVELOPMENT
            
    async def get_workload_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for workload optimization"""
        current_metrics = await self._collect_comprehensive_metrics()
        detected_workload = await self.auto_detect_workload()
        
        recommendations = {
            'current_workload': self.current_workload.value,
            'detected_optimal': detected_workload.value,
            'should_transition': detected_workload != self.current_workload,
            'metrics': current_metrics,
            'specific_recommendations': []
        }
        
        # Analyze specific inefficiencies
        if current_metrics.get('cpu_usage', 0) > 80:
            recommendations['specific_recommendations'].append({
                'type': 'performance',
                'issue': 'High CPU usage detected',
                'recommendation': 'Consider scaling up CPU-intensive services or transitioning to appropriate workload',
                'urgency': 'high'
            })
            
        if current_metrics.get('memory_usage', 0) > 85:
            recommendations['specific_recommendations'].append({
                'type': 'performance',
                'issue': 'High memory usage detected',
                'recommendation': 'Consider scaling up memory-intensive services',
                'urgency': 'high'
            })
            
        # Service-specific recommendations
        for service, metrics in current_metrics.get('services', {}).items():
            if metrics.get('cpu_percent', 0) > 90:
                recommendations['specific_recommendations'].append({
                    'type': 'service_scaling',
                    'service': service,
                    'issue': f'Service {service} CPU usage > 90%',
                    'recommendation': f'Scale up {service} instances',
                    'urgency': 'high'
                })
                
        return recommendations
        
    async def _collect_comprehensive_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system and service metrics"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_avg': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
            'services': {}
        }
        
        # Collect service metrics
        active_services = await self._get_running_services()
        for service in active_services:
            service_metrics = await self._get_service_resource_usage(service)
            if service_metrics:
                metrics['services'][service] = service_metrics
                
        return metrics

# Global orchestrator instance
orchestrator = WorkloadOrchestrator()

@app.on_startup
async def startup():
    """Start workload orchestrator"""
    logger.info("Starting Workload Orchestrator")
    
    # Auto-detect and set initial workload
    detected_workload = await orchestrator.auto_detect_workload()
    logger.info(f"Auto-detected workload: {detected_workload.value}")
    orchestrator.current_workload = detected_workload

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "workload-orchestrator"}

@app.get("/workload/current")
async def get_current_workload():
    """Get current workload configuration"""
    return {
        'current_workload': orchestrator.current_workload.value,
        'active_profile': orchestrator.active_profile,
        'transition_history': await get_recent_transitions()
    }

@app.post("/workload/transition/{target_workload}")
async def transition_workload_endpoint(target_workload: WorkloadType, force: bool = False):
    """Transition to a different workload"""
    result = await orchestrator.transition_workload(target_workload, force)
    return result

@app.get("/workload/detect")
async def auto_detect_workload():
    """Auto-detect optimal workload"""
    detected = await orchestrator.auto_detect_workload()
    return {
        'detected_workload': detected.value,
        'current_workload': orchestrator.current_workload.value,
        'should_transition': detected != orchestrator.current_workload
    }

@app.get("/workload/recommendations")
async def get_recommendations():
    """Get workload optimization recommendations"""
    return await orchestrator.get_workload_recommendations()

@app.get("/workload/profiles")
async def list_workload_profiles():
    """List all available workload profiles"""
    return {
        'profiles': [
            {
                'workload_type': wt.value,
                'profile_name': profile['profile_name'],
                'resource_allocation': profile['resource_allocation'],
                'performance_targets': profile['performance_targets']
            }
            for wt, profile in orchestrator.workload_profiles.items()
        ]
    }

@app.get("/metrics/system")
async def get_system_metrics():
    """Get current system metrics"""
    return await orchestrator._collect_comprehensive_metrics()

@app.get("/metrics/transitions")
async def get_recent_transitions(limit: int = 10):
    """Get recent workload transitions"""
    with sqlite3.connect(orchestrator.db_path) as conn:
        conn.row_factory = sqlite3.Row
        transitions = conn.execute("""
            SELECT * FROM workload_transitions 
            ORDER BY transition_time DESC 
            LIMIT ?
        """, (limit,)).fetchall()
        
    return [dict(transition) for transition in transitions]

@app.post("/scaling/decision/{service_name}")
async def make_scaling_decision(service_name: str, background_tasks: BackgroundTasks):
    """Make and execute scaling decision for a service"""
    # This would analyze current metrics and make intelligent scaling decisions
    current_metrics = await orchestrator._get_service_resource_usage(service_name)
    
    decision = {
        'service_name': service_name,
        'timestamp': datetime.now().isoformat(),
        'current_metrics': current_metrics,
        'decision': 'no_action',
        'reason': 'Within normal parameters'
    }
    
    # Simple scaling logic
    if current_metrics.get('cpu_percent', 0) > 80:
        current_instances = await orchestrator._get_service_instance_count(service_name)
        decision['decision'] = 'scale_up'
        decision['target_instances'] = current_instances + 1
        decision['reason'] = 'High CPU usage detected'
        
        # Execute scaling in background
        background_tasks.add_task(
            orchestrator._scale_service, 
            service_name, 
            decision['target_instances']
        )
        
    return decision

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8604))
    uvicorn.run(app, host="0.0.0.0", port=port)