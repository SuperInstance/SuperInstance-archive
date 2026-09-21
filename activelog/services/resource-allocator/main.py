#!/usr/bin/env python3
"""
Dynamic Resource Allocator
Intelligently allocates and reallocates resources based on real-time demand,
workload patterns, and predictive analytics
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from pydantic import BaseModel
import psutil
import docker
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Dynamic Resource Allocator", version="1.0.0")

class ResourceType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    NETWORK = "network"
    GPU = "gpu"

class AllocationStrategy(str, Enum):
    REACTIVE = "reactive"           # React to current usage
    PREDICTIVE = "predictive"      # Predict future needs
    BALANCED = "balanced"          # Balance current and predicted
    COST_OPTIMIZED = "cost_optimized"  # Minimize costs
    PERFORMANCE_FIRST = "performance_first"  # Maximize performance

@dataclass
class ResourceDemand:
    service_name: str
    resource_type: ResourceType
    current_usage: float
    predicted_usage: float
    priority: int
    urgency: float  # 0-1 scale

@dataclass
class AllocationDecision:
    service_name: str
    resource_type: ResourceType
    current_allocation: float
    target_allocation: float
    reason: str
    confidence: float
    estimated_cost_impact: float

class ResourceRequest(BaseModel):
    service_name: str
    resource_type: ResourceType
    amount: float
    duration_minutes: Optional[int] = None
    priority: int = 3

class AllocationPlan(BaseModel):
    plan_id: str
    strategy: AllocationStrategy
    total_resources_available: Dict[str, float]
    allocations: List[AllocationDecision]
    estimated_cost: float
    execution_time: str

class DynamicResourceAllocator:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "resource_allocator.db"
        self.models_path = Path(__file__).parent / "models"
        
        # Create directories
        self.db_path.parent.mkdir(exist_ok=True)
        self.models_path.mkdir(exist_ok=True)
        
        self._init_database()
        self._init_docker_client()
        self._init_prediction_models()
        
        # Resource state
        self.current_allocations = {}
        self.resource_pool = self._initialize_resource_pool()
        self.demand_history = []
        self.allocation_history = []
        
        # Prediction models
        self.usage_predictors = {}
        self.demand_forecaster = None
        
        # Configuration
        self.allocation_strategies = {
            AllocationStrategy.REACTIVE: self._reactive_allocation,
            AllocationStrategy.PREDICTIVE: self._predictive_allocation,
            AllocationStrategy.BALANCED: self._balanced_allocation,
            AllocationStrategy.COST_OPTIMIZED: self._cost_optimized_allocation,
            AllocationStrategy.PERFORMANCE_FIRST: self._performance_first_allocation
        }
        
    def _init_database(self):
        """Initialize SQLite database for resource allocation data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS resource_demands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    current_usage REAL,
                    predicted_usage REAL,
                    priority INTEGER,
                    urgency REAL
                );
                
                CREATE TABLE IF NOT EXISTS allocation_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    service_name TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    current_allocation REAL,
                    target_allocation REAL,
                    reason TEXT,
                    confidence REAL,
                    cost_impact REAL,
                    executed BOOLEAN DEFAULT FALSE,
                    execution_result TEXT
                );
                
                CREATE TABLE IF NOT EXISTS resource_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resource_type TEXT NOT NULL,
                    total_capacity REAL NOT NULL,
                    allocated_amount REAL DEFAULT 0,
                    available_amount REAL,
                    cost_per_unit REAL DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS usage_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    hour_of_day INTEGER,
                    day_of_week INTEGER,
                    average_usage REAL,
                    peak_usage REAL,
                    pattern_confidence REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS allocation_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT UNIQUE NOT NULL,
                    strategy TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_cost REAL,
                    execution_status TEXT,
                    plan_data JSON
                );
                
                CREATE INDEX IF NOT EXISTS idx_demands_timestamp ON resource_demands(timestamp);
                CREATE INDEX IF NOT EXISTS idx_decisions_service ON allocation_decisions(service_name);
                CREATE INDEX IF NOT EXISTS idx_patterns_service ON usage_patterns(service_name);
            """)
            
    def _init_docker_client(self):
        """Initialize Docker client for container resource management"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.warning(f"Docker client not available: {e}")
            self.docker_client = None
            
    def _init_prediction_models(self):
        """Initialize ML models for usage prediction"""
        self.cpu_predictor = RandomForestRegressor(n_estimators=50, random_state=42)
        self.memory_predictor = RandomForestRegressor(n_estimators=50, random_state=42)
        self.demand_forecaster = LinearRegression()
        
        # Load pre-trained models if available
        self._load_models()
        
    def _load_models(self):
        """Load pre-trained prediction models"""
        model_files = {
            'cpu_predictor': self.models_path / 'cpu_predictor.joblib',
            'memory_predictor': self.models_path / 'memory_predictor.joblib',
            'demand_forecaster': self.models_path / 'demand_forecaster.joblib'
        }
        
        try:
            import joblib
            for model_name, file_path in model_files.items():
                if file_path.exists():
                    model = joblib.load(file_path)
                    setattr(self, model_name, model)
                    logger.info(f"Loaded {model_name} model")
        except ImportError:
            logger.warning("joblib not available - models will be trained from scratch")
            
    def _initialize_resource_pool(self) -> Dict[str, Dict]:
        """Initialize available resource pool"""
        # Get system resources
        cpu_count = psutil.cpu_count()
        memory_total = psutil.virtual_memory().total // (1024 * 1024)  # MB
        disk_total = psutil.disk_usage('/').total // (1024 * 1024)  # MB
        
        pool = {
            ResourceType.CPU.value: {
                'total_capacity': cpu_count,
                'allocated': 0,
                'available': cpu_count,
                'cost_per_unit': 0.05  # $0.05 per vCPU hour
            },
            ResourceType.MEMORY.value: {
                'total_capacity': memory_total,
                'allocated': 0,
                'available': memory_total,
                'cost_per_unit': 0.01  # $0.01 per GB hour
            },
            ResourceType.STORAGE.value: {
                'total_capacity': disk_total,
                'allocated': 0,
                'available': disk_total,
                'cost_per_unit': 0.0001  # $0.0001 per GB hour
            },
            ResourceType.NETWORK.value: {
                'total_capacity': 10000,  # 10 Gbps in Mbps
                'allocated': 0,
                'available': 10000,
                'cost_per_unit': 0.001  # $0.001 per Mbps hour
            }
        }
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            for resource_type, config in pool.items():
                conn.execute("""
                    INSERT OR REPLACE INTO resource_pool 
                    (resource_type, total_capacity, available_amount, cost_per_unit)
                    VALUES (?, ?, ?, ?)
                """, (
                    resource_type,
                    config['total_capacity'],
                    config['available'],
                    config['cost_per_unit']
                ))
                
        return pool
        
    async def collect_resource_demands(self) -> List[ResourceDemand]:
        """Collect current resource demands from all services"""
        demands = []
        
        # Get active services from workload orchestrator
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8604/metrics/system') as response:
                    if response.status == 200:
                        metrics = await response.json()
                        
                        for service_name, service_metrics in metrics.get('services', {}).items():
                            # CPU demand
                            cpu_usage = service_metrics.get('cpu_usage', 0)
                            cpu_predicted = await self._predict_resource_usage(
                                service_name, ResourceType.CPU, cpu_usage
                            )
                            
                            if cpu_usage > 0 or cpu_predicted > 0:
                                demands.append(ResourceDemand(
                                    service_name=service_name,
                                    resource_type=ResourceType.CPU,
                                    current_usage=cpu_usage,
                                    predicted_usage=cpu_predicted,
                                    priority=self._get_service_priority(service_name),
                                    urgency=self._calculate_urgency(cpu_usage, cpu_predicted)
                                ))
                                
                            # Memory demand
                            memory_usage = service_metrics.get('memory_usage', 0)
                            memory_predicted = await self._predict_resource_usage(
                                service_name, ResourceType.MEMORY, memory_usage
                            )
                            
                            if memory_usage > 0 or memory_predicted > 0:
                                demands.append(ResourceDemand(
                                    service_name=service_name,
                                    resource_type=ResourceType.MEMORY,
                                    current_usage=memory_usage,
                                    predicted_usage=memory_predicted,
                                    priority=self._get_service_priority(service_name),
                                    urgency=self._calculate_urgency(memory_usage, memory_predicted)
                                ))
                                
        except Exception as e:
            logger.error(f"Failed to collect resource demands: {e}")
            
        # Store demands in database
        await self._store_demands(demands)
        
        return demands
        
    def _get_service_priority(self, service_name: str) -> int:
        """Get service priority (1=highest, 5=lowest)"""
        priority_map = {
            'trading-engine': 1,
            'settlement-engine': 1,
            'compliance-engine': 2,
            'market-data': 2,
            'api-gateway': 2,
            'wallet-service': 3,
            'analytics': 3,
            'observability-stack': 3,
            'backup-dr': 4,
            'dev-productivity': 4
        }
        return priority_map.get(service_name, 3)
        
    def _calculate_urgency(self, current: float, predicted: float) -> float:
        """Calculate urgency score (0-1)"""
        if current == 0 and predicted == 0:
            return 0.0
            
        # Urgency increases with usage level and growth rate
        usage_urgency = min(current / 100, 1.0)  # Normalize to 0-1
        growth_urgency = min(abs(predicted - current) / 50, 1.0)  # Growth rate impact
        
        return (usage_urgency * 0.7) + (growth_urgency * 0.3)
        
    async def _predict_resource_usage(self, service_name: str, resource_type: ResourceType, current_usage: float) -> float:
        """Predict future resource usage"""
        try:
            # Get historical usage data
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT current_usage FROM resource_demands 
                    WHERE service_name = ? AND resource_type = ?
                    ORDER BY timestamp DESC LIMIT 10
                """, (service_name, resource_type.value))
                
                history = [row[0] for row in cursor.fetchall()]
                
            if len(history) < 3:
                # Not enough history, use simple prediction
                return current_usage * 1.1  # Assume 10% growth
                
            # Use time series prediction
            X = np.array(range(len(history))).reshape(-1, 1)
            y = np.array(history)
            
            if resource_type == ResourceType.CPU:
                self.cpu_predictor.fit(X, y)
                predicted = self.cpu_predictor.predict([[len(history)]])[0]
            elif resource_type == ResourceType.MEMORY:
                self.memory_predictor.fit(X, y)
                predicted = self.memory_predictor.predict([[len(history)]])[0]
            else:
                # Use linear regression for other resources
                self.demand_forecaster.fit(X, y)
                predicted = self.demand_forecaster.predict([[len(history)]])[0]
                
            return max(0, predicted)
            
        except Exception as e:
            logger.warning(f"Prediction failed for {service_name} {resource_type.value}: {e}")
            return current_usage
            
    async def _store_demands(self, demands: List[ResourceDemand]):
        """Store resource demands in database"""
        with sqlite3.connect(self.db_path) as conn:
            for demand in demands:
                conn.execute("""
                    INSERT INTO resource_demands 
                    (service_name, resource_type, current_usage, predicted_usage, priority, urgency)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    demand.service_name,
                    demand.resource_type.value,
                    demand.current_usage,
                    demand.predicted_usage,
                    demand.priority,
                    demand.urgency
                ))
                
    async def create_allocation_plan(self, strategy: AllocationStrategy) -> AllocationPlan:
        """Create a resource allocation plan using specified strategy"""
        demands = await self.collect_resource_demands()
        
        if not demands:
            return AllocationPlan(
                plan_id=f"empty-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                strategy=strategy,
                total_resources_available=self._get_available_resources(),
                allocations=[],
                estimated_cost=0.0,
                execution_time=datetime.now().isoformat()
            )
            
        # Apply allocation strategy
        allocation_func = self.allocation_strategies[strategy]
        allocations = await allocation_func(demands)
        
        # Calculate total cost
        total_cost = sum(decision.estimated_cost_impact for decision in allocations)
        
        plan = AllocationPlan(
            plan_id=f"{strategy.value}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            strategy=strategy,
            total_resources_available=self._get_available_resources(),
            allocations=allocations,
            estimated_cost=total_cost,
            execution_time=datetime.now().isoformat()
        )
        
        # Store plan in database
        await self._store_allocation_plan(plan)
        
        return plan
        
    def _get_available_resources(self) -> Dict[str, float]:
        """Get currently available resources"""
        return {
            resource_type: config['available']
            for resource_type, config in self.resource_pool.items()
        }
        
    async def _reactive_allocation(self, demands: List[ResourceDemand]) -> List[AllocationDecision]:
        """Reactive allocation based on current usage"""
        decisions = []
        
        # Group demands by resource type
        demands_by_type = {}
        for demand in demands:
            resource_type = demand.resource_type.value
            if resource_type not in demands_by_type:
                demands_by_type[resource_type] = []
            demands_by_type[resource_type].append(demand)
            
        for resource_type, resource_demands in demands_by_type.items():
            available = self.resource_pool[resource_type]['available']
            
            # Sort by priority and urgency
            resource_demands.sort(key=lambda d: (d.priority, -d.urgency))
            
            for demand in resource_demands:
                current_allocation = await self._get_current_allocation(
                    demand.service_name, demand.resource_type
                )
                
                # Calculate needed allocation based on current usage + buffer
                needed = demand.current_usage * 1.2  # 20% buffer
                target_allocation = max(needed, current_allocation)
                
                if target_allocation > current_allocation and available >= (target_allocation - current_allocation):
                    available -= (target_allocation - current_allocation)
                    
                    cost_impact = self._calculate_cost_impact(
                        resource_type, current_allocation, target_allocation
                    )
                    
                    decisions.append(AllocationDecision(
                        service_name=demand.service_name,
                        resource_type=demand.resource_type,
                        current_allocation=current_allocation,
                        target_allocation=target_allocation,
                        reason=f"Reactive allocation for current usage {demand.current_usage:.2f}",
                        confidence=0.8,
                        estimated_cost_impact=cost_impact
                    ))
                    
        return decisions
        
    async def _predictive_allocation(self, demands: List[ResourceDemand]) -> List[AllocationDecision]:
        """Predictive allocation based on forecasted usage"""
        decisions = []
        
        for demand in demands:
            if demand.predicted_usage > demand.current_usage:
                current_allocation = await self._get_current_allocation(
                    demand.service_name, demand.resource_type
                )
                
                # Allocate based on predicted usage + buffer
                target_allocation = demand.predicted_usage * 1.15  # 15% buffer
                
                if target_allocation > current_allocation:
                    resource_type = demand.resource_type.value
                    available = self.resource_pool[resource_type]['available']
                    needed = target_allocation - current_allocation
                    
                    if available >= needed:
                        cost_impact = self._calculate_cost_impact(
                            resource_type, current_allocation, target_allocation
                        )
                        
                        decisions.append(AllocationDecision(
                            service_name=demand.service_name,
                            resource_type=demand.resource_type,
                            current_allocation=current_allocation,
                            target_allocation=target_allocation,
                            reason=f"Predictive allocation for forecasted usage {demand.predicted_usage:.2f}",
                            confidence=0.6,
                            estimated_cost_impact=cost_impact
                        ))
                        
                        self.resource_pool[resource_type]['available'] -= needed
                        
        return decisions
        
    async def _balanced_allocation(self, demands: List[ResourceDemand]) -> List[AllocationDecision]:
        """Balanced allocation considering both current and predicted usage"""
        decisions = []
        
        for demand in demands:
            current_allocation = await self._get_current_allocation(
                demand.service_name, demand.resource_type
            )
            
            # Balance current and predicted usage
            balanced_usage = (demand.current_usage * 0.6) + (demand.predicted_usage * 0.4)
            target_allocation = balanced_usage * 1.1  # 10% buffer
            
            if target_allocation > current_allocation:
                resource_type = demand.resource_type.value
                available = self.resource_pool[resource_type]['available']
                needed = target_allocation - current_allocation
                
                if available >= needed:
                    cost_impact = self._calculate_cost_impact(
                        resource_type, current_allocation, target_allocation
                    )
                    
                    decisions.append(AllocationDecision(
                        service_name=demand.service_name,
                        resource_type=demand.resource_type,
                        current_allocation=current_allocation,
                        target_allocation=target_allocation,
                        reason=f"Balanced allocation (current: {demand.current_usage:.2f}, predicted: {demand.predicted_usage:.2f})",
                        confidence=0.7,
                        estimated_cost_impact=cost_impact
                    ))
                    
                    self.resource_pool[resource_type]['available'] -= needed
                    
        return decisions
        
    async def _cost_optimized_allocation(self, demands: List[ResourceDemand]) -> List[AllocationDecision]:
        """Cost-optimized allocation minimizing resource costs"""
        decisions = []
        
        # Sort by cost efficiency (usage per cost)
        efficiency_sorted = []
        for demand in demands:
            resource_type = demand.resource_type.value
            cost_per_unit = self.resource_pool[resource_type]['cost_per_unit']
            efficiency = demand.current_usage / max(cost_per_unit, 0.001)
            efficiency_sorted.append((demand, efficiency))
            
        efficiency_sorted.sort(key=lambda x: x[1], reverse=True)
        
        for demand, efficiency in efficiency_sorted:
            current_allocation = await self._get_current_allocation(
                demand.service_name, demand.resource_type
            )
            
            # Minimal allocation - just enough for current usage
            target_allocation = demand.current_usage * 1.05  # 5% buffer only
            
            if target_allocation > current_allocation:
                resource_type = demand.resource_type.value
                available = self.resource_pool[resource_type]['available']
                needed = target_allocation - current_allocation
                
                if available >= needed:
                    cost_impact = self._calculate_cost_impact(
                        resource_type, current_allocation, target_allocation
                    )
                    
                    decisions.append(AllocationDecision(
                        service_name=demand.service_name,
                        resource_type=demand.resource_type,
                        current_allocation=current_allocation,
                        target_allocation=target_allocation,
                        reason=f"Cost-optimized minimal allocation (efficiency: {efficiency:.2f})",
                        confidence=0.85,
                        estimated_cost_impact=cost_impact
                    ))
                    
                    self.resource_pool[resource_type]['available'] -= needed
                    
        return decisions
        
    async def _performance_first_allocation(self, demands: List[ResourceDemand]) -> List[AllocationDecision]:
        """Performance-first allocation maximizing performance"""
        decisions = []
        
        # Sort by priority and urgency
        priority_sorted = sorted(demands, key=lambda d: (d.priority, -d.urgency))
        
        for demand in priority_sorted:
            current_allocation = await self._get_current_allocation(
                demand.service_name, demand.resource_type
            )
            
            # Generous allocation for performance
            performance_usage = max(demand.current_usage, demand.predicted_usage)
            target_allocation = performance_usage * 1.5  # 50% buffer for performance
            
            resource_type = demand.resource_type.value
            available = self.resource_pool[resource_type]['available']
            needed = max(0, target_allocation - current_allocation)
            
            if available >= needed:
                cost_impact = self._calculate_cost_impact(
                    resource_type, current_allocation, target_allocation
                )
                
                decisions.append(AllocationDecision(
                    service_name=demand.service_name,
                    resource_type=demand.resource_type,
                    current_allocation=current_allocation,
                    target_allocation=target_allocation,
                    reason=f"Performance-first allocation (priority: {demand.priority})",
                    confidence=0.9,
                    estimated_cost_impact=cost_impact
                ))
                
                self.resource_pool[resource_type]['available'] -= needed
                
        return decisions
        
    async def _get_current_allocation(self, service_name: str, resource_type: ResourceType) -> float:
        """Get current resource allocation for a service"""
        key = f"{service_name}_{resource_type.value}"
        return self.current_allocations.get(key, 0.0)
        
    def _calculate_cost_impact(self, resource_type: str, current: float, target: float) -> float:
        """Calculate cost impact of allocation change"""
        cost_per_unit = self.resource_pool[resource_type]['cost_per_unit']
        change = target - current
        return change * cost_per_unit  # Hourly cost impact
        
    async def _store_allocation_plan(self, plan: AllocationPlan):
        """Store allocation plan in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO allocation_plans 
                (plan_id, strategy, total_cost, execution_status, plan_data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                plan.plan_id,
                plan.strategy.value,
                plan.estimated_cost,
                'created',
                json.dumps({
                    'allocations_count': len(plan.allocations),
                    'total_resources': plan.total_resources_available
                })
            ))
            
    async def execute_allocation_plan(self, plan: AllocationPlan) -> Dict[str, Any]:
        """Execute a resource allocation plan"""
        execution_results = {
            'plan_id': plan.plan_id,
            'started_at': datetime.now().isoformat(),
            'successful_allocations': 0,
            'failed_allocations': 0,
            'errors': []
        }
        
        for decision in plan.allocations:
            try:
                success = await self._execute_allocation_decision(decision)
                if success:
                    execution_results['successful_allocations'] += 1
                    
                    # Update current allocations
                    key = f"{decision.service_name}_{decision.resource_type.value}"
                    self.current_allocations[key] = decision.target_allocation
                    
                    # Update resource pool
                    resource_type = decision.resource_type.value
                    change = decision.target_allocation - decision.current_allocation
                    self.resource_pool[resource_type]['allocated'] += change
                    self.resource_pool[resource_type]['available'] -= change
                else:
                    execution_results['failed_allocations'] += 1
                    
                # Store execution result
                await self._store_allocation_decision(decision, success)
                
            except Exception as e:
                execution_results['failed_allocations'] += 1
                execution_results['errors'].append(f"{decision.service_name}: {str(e)}")
                
        execution_results['completed_at'] = datetime.now().isoformat()
        execution_results['success_rate'] = (
            execution_results['successful_allocations'] / 
            max(len(plan.allocations), 1)
        ) * 100
        
        return execution_results
        
    async def _execute_allocation_decision(self, decision: AllocationDecision) -> bool:
        """Execute a single allocation decision"""
        try:
            if decision.resource_type == ResourceType.CPU:
                return await self._allocate_cpu(decision)
            elif decision.resource_type == ResourceType.MEMORY:
                return await self._allocate_memory(decision)
            elif decision.resource_type == ResourceType.STORAGE:
                return await self._allocate_storage(decision)
            else:
                logger.warning(f"Allocation not implemented for {decision.resource_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to execute allocation for {decision.service_name}: {e}")
            return False
            
    async def _allocate_cpu(self, decision: AllocationDecision) -> bool:
        """Allocate CPU resources to a service"""
        if not self.docker_client:
            return False
            
        try:
            # Find containers for the service
            containers = self.docker_client.containers.list(
                filters={'label': f'service={decision.service_name}'}
            )
            
            if not containers:
                logger.warning(f"No containers found for service {decision.service_name}")
                return False
                
            # Calculate CPU limit in nanocpus
            cpu_limit = int(decision.target_allocation * 1000000000)
            
            for container in containers:
                container.update(cpu_quota=cpu_limit, cpu_period=100000)
                
            logger.info(f"Allocated {decision.target_allocation} CPU cores to {decision.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"CPU allocation failed for {decision.service_name}: {e}")
            return False
            
    async def _allocate_memory(self, decision: AllocationDecision) -> bool:
        """Allocate memory resources to a service"""
        if not self.docker_client:
            return False
            
        try:
            containers = self.docker_client.containers.list(
                filters={'label': f'service={decision.service_name}'}
            )
            
            if not containers:
                return False
                
            # Calculate memory limit in bytes
            memory_limit = int(decision.target_allocation * 1024 * 1024)
            
            for container in containers:
                container.update(mem_limit=memory_limit)
                
            logger.info(f"Allocated {decision.target_allocation} MB memory to {decision.service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Memory allocation failed for {decision.service_name}: {e}")
            return False
            
    async def _allocate_storage(self, decision: AllocationDecision) -> bool:
        """Allocate storage resources to a service"""
        # Storage allocation would typically involve volume management
        # This is a simplified implementation
        logger.info(f"Storage allocation simulated for {decision.service_name}: {decision.target_allocation} MB")
        return True
        
    async def _store_allocation_decision(self, decision: AllocationDecision, success: bool):
        """Store allocation decision result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO allocation_decisions 
                (service_name, resource_type, current_allocation, target_allocation, 
                 reason, confidence, cost_impact, executed, execution_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.service_name,
                decision.resource_type.value,
                decision.current_allocation,
                decision.target_allocation,
                decision.reason,
                decision.confidence,
                decision.estimated_cost_impact,
                success,
                'success' if success else 'failed'
            ))
            
    async def get_allocation_analytics(self) -> Dict[str, Any]:
        """Get analytics about resource allocation patterns"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Allocation success rate
            success_rate = conn.execute("""
                SELECT 
                    AVG(CASE WHEN executed = 1 THEN 100.0 ELSE 0.0 END) as success_rate,
                    COUNT(*) as total_decisions
                FROM allocation_decisions 
                WHERE timestamp > datetime('now', '-24 hours')
            """).fetchone()
            
            # Resource utilization by type
            utilization = conn.execute("""
                SELECT 
                    resource_type,
                    AVG(current_usage) as avg_usage,
                    MAX(current_usage) as peak_usage,
                    COUNT(*) as measurements
                FROM resource_demands 
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY resource_type
            """).fetchall()
            
            # Cost trends
            cost_trends = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(cost_impact) as daily_cost_impact
                FROM allocation_decisions 
                WHERE timestamp > datetime('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            """).fetchall()
            
        return {
            'success_rate': dict(success_rate) if success_rate else {},
            'resource_utilization': [dict(row) for row in utilization],
            'cost_trends': [dict(row) for row in cost_trends],
            'current_allocations': self.current_allocations,
            'resource_pool_status': self.resource_pool
        }

# Global resource allocator instance
resource_allocator = DynamicResourceAllocator()

@app.on_startup
async def startup():
    """Start dynamic resource allocator"""
    logger.info("Starting Dynamic Resource Allocator")
    
    # Start background allocation monitoring
    asyncio.create_task(allocation_monitoring_loop())

async def allocation_monitoring_loop():
    """Background loop for continuous resource monitoring and allocation"""
    while True:
        try:
            # Collect current demands
            demands = await resource_allocator.collect_resource_demands()
            
            if demands:
                # Create and execute balanced allocation plan
                plan = await resource_allocator.create_allocation_plan(AllocationStrategy.BALANCED)
                
                # Execute only high-confidence decisions automatically
                high_confidence_plan = AllocationPlan(
                    plan_id=f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                    strategy=plan.strategy,
                    total_resources_available=plan.total_resources_available,
                    allocations=[
                        decision for decision in plan.allocations 
                        if decision.confidence >= 0.8
                    ],
                    estimated_cost=sum(
                        decision.estimated_cost_impact for decision in plan.allocations 
                        if decision.confidence >= 0.8
                    ),
                    execution_time=datetime.now().isoformat()
                )
                
                if high_confidence_plan.allocations:
                    results = await resource_allocator.execute_allocation_plan(high_confidence_plan)
                    logger.info(f"Auto-executed {results['successful_allocations']} allocations")
                    
        except Exception as e:
            logger.error(f"Error in allocation monitoring loop: {e}")
            
        # Wait before next iteration
        await asyncio.sleep(60)  # Run every minute

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "dynamic-resource-allocator"}

@app.get("/resources/pool")
async def get_resource_pool():
    """Get current resource pool status"""
    return resource_allocator.resource_pool

@app.get("/resources/demands")
async def get_current_demands():
    """Get current resource demands"""
    demands = await resource_allocator.collect_resource_demands()
    return [
        {
            'service_name': d.service_name,
            'resource_type': d.resource_type.value,
            'current_usage': d.current_usage,
            'predicted_usage': d.predicted_usage,
            'priority': d.priority,
            'urgency': d.urgency
        }
        for d in demands
    ]

@app.post("/allocation/plan/{strategy}")
async def create_allocation_plan_endpoint(strategy: AllocationStrategy):
    """Create a resource allocation plan"""
    plan = await resource_allocator.create_allocation_plan(strategy)
    return plan

@app.post("/allocation/execute")
async def execute_allocation_plan_endpoint(plan: AllocationPlan):
    """Execute a resource allocation plan"""
    results = await resource_allocator.execute_allocation_plan(plan)
    return results

@app.post("/resources/request")
async def request_resources(request: ResourceRequest):
    """Request additional resources for a service"""
    # Create a synthetic demand
    demand = ResourceDemand(
        service_name=request.service_name,
        resource_type=request.resource_type,
        current_usage=request.amount,
        predicted_usage=request.amount,
        priority=request.priority,
        urgency=0.8
    )
    
    # Create allocation plan
    plan = await resource_allocator._balanced_allocation([demand])
    
    if plan:
        execution_plan = AllocationPlan(
            plan_id=f"request-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            strategy=AllocationStrategy.BALANCED,
            total_resources_available=resource_allocator._get_available_resources(),
            allocations=plan,
            estimated_cost=sum(d.estimated_cost_impact for d in plan),
            execution_time=datetime.now().isoformat()
        )
        
        results = await resource_allocator.execute_allocation_plan(execution_plan)
        return {
            'request_id': execution_plan.plan_id,
            'allocated': results['successful_allocations'] > 0,
            'execution_results': results
        }
    else:
        return {
            'allocated': False,
            'reason': 'Insufficient resources available'
        }

@app.get("/analytics/allocation")
async def get_allocation_analytics():
    """Get resource allocation analytics"""
    return await resource_allocator.get_allocation_analytics()

@app.websocket("/ws/resource-monitoring")
async def websocket_resource_monitoring(websocket: WebSocket):
    """WebSocket for real-time resource monitoring"""
    await websocket.accept()
    
    try:
        while True:
            # Send current resource status
            status = {
                'timestamp': datetime.now().isoformat(),
                'resource_pool': resource_allocator.resource_pool,
                'current_allocations': resource_allocator.current_allocations,
                'demands': await resource_allocator.collect_resource_demands()
            }
            
            # Convert demands to serializable format
            status['demands'] = [
                {
                    'service_name': d.service_name,
                    'resource_type': d.resource_type.value,
                    'current_usage': d.current_usage,
                    'predicted_usage': d.predicted_usage,
                    'urgency': d.urgency
                }
                for d in status['demands']
            ]
            
            await websocket.send_text(json.dumps(status))
            await asyncio.sleep(30)  # Send updates every 30 seconds
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8606))
    uvicorn.run(app, host="0.0.0.0", port=port)