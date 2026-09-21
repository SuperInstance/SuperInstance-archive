"""
ActiveLog Simulation Engine - Business Process Simulation

This module provides comprehensive business process simulation capabilities including:
- Workflow modeling and optimization
- Resource allocation simulation
- Bottleneck identification and analysis
- Process performance prediction
- Cost and time optimization
- Quality and compliance modeling
- Multi-scenario business process analysis
- Real-time process monitoring and adjustment
"""

import asyncio
import json
import logging
import random
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessStatus(Enum):
    """Status of a business process"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ResourceType(Enum):
    """Types of business resources"""
    HUMAN = "human"
    EQUIPMENT = "equipment"
    SOFTWARE = "software"
    FACILITY = "facility"
    FINANCIAL = "financial"
    MATERIAL = "material"
    INFORMATION = "information"


class ProcessPriority(Enum):
    """Priority levels for processes"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class SimulationMode(Enum):
    """Simulation execution modes"""
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"
    MONTE_CARLO = "monte_carlo"
    DISCRETE_EVENT = "discrete_event"
    CONTINUOUS = "continuous"
    HYBRID = "hybrid"


@dataclass
class Resource:
    """Represents a business resource"""
    resource_id: str
    name: str
    resource_type: ResourceType
    capacity: float
    cost_per_hour: float
    availability_hours: Dict[str, Tuple[int, int]] = field(default_factory=dict)  # day -> (start_hour, end_hour)
    utilization_rate: float = 0.0
    efficiency_factor: float = 1.0
    skill_level: float = 1.0  # 0.5 to 2.0
    maintenance_schedule: List[Tuple[datetime, datetime]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessStep:
    """Individual step in a business process"""
    step_id: str
    name: str
    description: str
    required_resources: List[Tuple[str, float]]  # (resource_id, quantity)
    duration_min: float  # minutes
    duration_max: float
    duration_distribution: str = "normal"  # normal, uniform, exponential, etc.
    cost: float = 0.0
    failure_rate: float = 0.0  # probability of failure
    quality_impact: float = 1.0
    dependencies: List[str] = field(default_factory=list)  # step_ids that must complete first
    parallel_steps: List[str] = field(default_factory=list)  # steps that can run in parallel
    conditions: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)


@dataclass
class BusinessProcess:
    """Complete business process definition"""
    process_id: str
    name: str
    description: str
    steps: List[ProcessStep]
    start_conditions: Dict[str, Any] = field(default_factory=dict)
    end_conditions: Dict[str, Any] = field(default_factory=dict)
    priority: ProcessPriority = ProcessPriority.NORMAL
    sla_hours: Optional[float] = None  # Service Level Agreement
    compliance_requirements: List[str] = field(default_factory=list)
    process_owner: str = ""
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessInstance:
    """Runtime instance of a business process"""
    instance_id: str
    process_id: str
    status: ProcessStatus
    current_step: Optional[str] = None
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    step_start_times: Dict[str, datetime] = field(default_factory=dict)
    step_end_times: Dict[str, datetime] = field(default_factory=dict)
    resource_assignments: Dict[str, List[str]] = field(default_factory=dict)  # step_id -> resource_ids
    total_cost: float = 0.0
    quality_score: float = 1.0
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulationScenario:
    """Simulation scenario configuration"""
    scenario_id: str
    name: str
    description: str
    processes: List[str]  # process_ids to simulate
    resources: List[str]  # resource_ids available
    simulation_duration: float  # hours
    arrival_rate: float  # processes per hour
    arrival_pattern: str = "poisson"  # poisson, constant, batch, etc.
    resource_constraints: Dict[str, float] = field(default_factory=dict)
    external_factors: Dict[str, Any] = field(default_factory=dict)
    objectives: List[str] = field(default_factory=list)  # minimize_cost, maximize_throughput, etc.


@dataclass
class SimulationResult:
    """Results from a simulation run"""
    result_id: str
    scenario_id: str
    mode: SimulationMode
    total_processes: int
    completed_processes: int
    failed_processes: int
    average_completion_time: float
    total_cost: float
    resource_utilization: Dict[str, float]
    bottlenecks: List[Tuple[str, str, float]]  # (step_id/resource_id, type, severity)
    quality_metrics: Dict[str, float]
    throughput: float  # processes per hour
    cycle_time: float  # average time from start to finish
    wait_time: float  # average waiting time
    process_efficiency: float
    sla_compliance: float  # percentage of processes meeting SLA
    recommendations: List[str] = field(default_factory=list)
    executed_at: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationSuggestion:
    """Optimization suggestion for business processes"""
    suggestion_id: str
    type: str  # resource_adjustment, process_redesign, scheduling_change, etc.
    description: str
    expected_impact: Dict[str, float]  # metric -> improvement
    implementation_cost: float
    implementation_time: float  # days
    confidence: float  # 0-1
    affected_processes: List[str]
    affected_resources: List[str]
    priority: int  # 1-5


class ProcessSimulator(ABC):
    """Abstract base for process simulation engines"""
    
    @abstractmethod
    async def simulate(self, scenario: SimulationScenario, mode: SimulationMode) -> SimulationResult:
        """Run simulation for given scenario"""
        pass
    
    @abstractmethod
    async def optimize_process(self, process: BusinessProcess, constraints: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """Optimize a business process"""
        pass


class ResourceManager(ABC):
    """Abstract resource management interface"""
    
    @abstractmethod
    async def allocate_resources(self, step: ProcessStep, instance: ProcessInstance, 
                               available_resources: List[Resource]) -> List[Resource]:
        """Allocate resources for a process step"""
        pass
    
    @abstractmethod
    async def release_resources(self, resources: List[Resource], instance: ProcessInstance) -> None:
        """Release resources after step completion"""
        pass


class ProcessAnalyzer(ABC):
    """Abstract process analysis interface"""
    
    @abstractmethod
    async def analyze_bottlenecks(self, results: List[SimulationResult]) -> List[Tuple[str, str, float]]:
        """Analyze bottlenecks from simulation results"""
        pass
    
    @abstractmethod
    async def predict_performance(self, process: BusinessProcess, resources: List[Resource]) -> Dict[str, float]:
        """Predict process performance metrics"""
        pass


class DiscreteEventSimulator(ProcessSimulator):
    """Discrete event simulation engine for business processes"""
    
    def __init__(self):
        self.event_queue = []
        self.current_time = 0.0
        self.statistics = {}
        
    async def simulate(self, scenario: SimulationScenario, mode: SimulationMode) -> SimulationResult:
        """Run discrete event simulation"""
        try:
            # Initialize simulation
            await self._initialize_simulation(scenario)
            
            # Generate process arrivals
            arrivals = await self._generate_arrivals(scenario)
            
            # Run simulation
            instances = await self._run_simulation(scenario, arrivals, mode)
            
            # Analyze results
            result = await self._analyze_results(scenario, instances, mode)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in simulation: {e}")
            return SimulationResult(
                result_id=str(uuid4()),
                scenario_id=scenario.scenario_id,
                mode=mode,
                total_processes=0,
                completed_processes=0,
                failed_processes=0,
                average_completion_time=0.0,
                total_cost=0.0,
                resource_utilization={},
                bottlenecks=[],
                quality_metrics={},
                throughput=0.0,
                cycle_time=0.0,
                wait_time=0.0,
                process_efficiency=0.0,
                sla_compliance=0.0
            )
    
    async def optimize_process(self, process: BusinessProcess, constraints: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """Optimize process using simulation-based analysis"""
        try:
            suggestions = []
            
            # Analyze current process
            current_metrics = await self._analyze_current_process(process)
            
            # Generate optimization suggestions
            
            # 1. Resource optimization
            resource_suggestions = await self._suggest_resource_optimizations(process, current_metrics)
            suggestions.extend(resource_suggestions)
            
            # 2. Process flow optimization
            flow_suggestions = await self._suggest_flow_optimizations(process, current_metrics)
            suggestions.extend(flow_suggestions)
            
            # 3. Scheduling optimization
            scheduling_suggestions = await self._suggest_scheduling_optimizations(process, current_metrics)
            suggestions.extend(scheduling_suggestions)
            
            # 4. Quality optimization
            quality_suggestions = await self._suggest_quality_optimizations(process, current_metrics)
            suggestions.extend(quality_suggestions)
            
            # Sort by expected impact and confidence
            suggestions.sort(key=lambda x: x.expected_impact.get('efficiency', 0) * x.confidence, reverse=True)
            
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            logger.error(f"Error optimizing process: {e}")
            return []
    
    async def _initialize_simulation(self, scenario: SimulationScenario):
        """Initialize simulation state"""
        self.current_time = 0.0
        self.event_queue = []
        self.statistics = {
            'total_instances': 0,
            'completed_instances': 0,
            'failed_instances': 0,
            'total_cost': 0.0,
            'resource_usage': {},
            'step_durations': {},
            'wait_times': []
        }
    
    async def _generate_arrivals(self, scenario: SimulationScenario) -> List[float]:
        """Generate process arrival times"""
        arrivals = []
        
        if scenario.arrival_pattern == "poisson":
            # Poisson arrival process
            current_time = 0.0
            while current_time < scenario.simulation_duration:
                # Exponential inter-arrival times
                inter_arrival = np.random.exponential(1.0 / scenario.arrival_rate)
                current_time += inter_arrival
                if current_time < scenario.simulation_duration:
                    arrivals.append(current_time)
        
        elif scenario.arrival_pattern == "constant":
            # Constant inter-arrival times
            inter_arrival = 1.0 / scenario.arrival_rate
            current_time = 0.0
            while current_time < scenario.simulation_duration:
                current_time += inter_arrival
                if current_time < scenario.simulation_duration:
                    arrivals.append(current_time)
        
        elif scenario.arrival_pattern == "batch":
            # Batch arrivals
            batch_size = 5
            batch_interval = batch_size / scenario.arrival_rate
            current_time = 0.0
            while current_time < scenario.simulation_duration:
                for _ in range(batch_size):
                    arrivals.append(current_time)
                current_time += batch_interval
        
        return arrivals
    
    async def _run_simulation(self, scenario: SimulationScenario, arrivals: List[float], 
                            mode: SimulationMode) -> List[ProcessInstance]:
        """Run the actual simulation"""
        instances = []
        active_instances = {}
        
        # Create initial events for process arrivals
        for arrival_time in arrivals:
            process_id = random.choice(scenario.processes)
            instance = ProcessInstance(
                instance_id=str(uuid4()),
                process_id=process_id,
                status=ProcessStatus.NOT_STARTED,
                started_at=datetime.now() + timedelta(hours=arrival_time)
            )
            
            # Add to event queue
            self.event_queue.append({
                'time': arrival_time,
                'type': 'process_arrival',
                'instance': instance
            })
        
        # Sort events by time
        self.event_queue.sort(key=lambda x: x['time'])
        
        # Process events
        for event in self.event_queue:
            self.current_time = event['time']
            
            if event['type'] == 'process_arrival':
                instance = event['instance']
                active_instances[instance.instance_id] = instance
                
                # Start the process
                await self._start_process_instance(instance, scenario, mode)
                
            elif event['type'] == 'step_completion':
                instance = event['instance']
                step_id = event['step_id']
                
                await self._complete_step(instance, step_id, scenario, mode)
                
                # Check if process is complete
                if await self._is_process_complete(instance, scenario):
                    instance.status = ProcessStatus.COMPLETED
                    instance.completed_at = datetime.now() + timedelta(hours=self.current_time)
                    instances.append(instance)
                    del active_instances[instance.instance_id]
        
        # Add any remaining active instances
        instances.extend(active_instances.values())
        
        return instances
    
    async def _start_process_instance(self, instance: ProcessInstance, scenario: SimulationScenario, mode: SimulationMode):
        """Start a process instance"""
        instance.status = ProcessStatus.IN_PROGRESS
        
        # Find first step(s) to execute
        process = await self._get_process_definition(instance.process_id, scenario)
        if process:
            first_steps = await self._find_first_steps(process)
            
            for step_id in first_steps:
                await self._schedule_step(instance, step_id, scenario, mode)
    
    async def _schedule_step(self, instance: ProcessInstance, step_id: str, 
                           scenario: SimulationScenario, mode: SimulationMode):
        """Schedule a process step for execution"""
        process = await self._get_process_definition(instance.process_id, scenario)
        step = next((s for s in process.steps if s.step_id == step_id), None)
        
        if step:
            # Simulate step duration
            duration = await self._simulate_step_duration(step, mode)
            
            # Schedule completion event
            completion_time = self.current_time + (duration / 60.0)  # Convert to hours
            
            self.event_queue.append({
                'time': completion_time,
                'type': 'step_completion',
                'instance': instance,
                'step_id': step_id
            })
            
            # Update instance
            instance.step_start_times[step_id] = datetime.now() + timedelta(hours=self.current_time)
            
            # Sort event queue
            self.event_queue.sort(key=lambda x: x['time'])
    
    async def _complete_step(self, instance: ProcessInstance, step_id: str, 
                           scenario: SimulationScenario, mode: SimulationMode):
        """Complete a process step"""
        instance.completed_steps.append(step_id)
        instance.step_end_times[step_id] = datetime.now() + timedelta(hours=self.current_time)
        
        # Calculate step cost and quality impact
        process = await self._get_process_definition(instance.process_id, scenario)
        step = next((s for s in process.steps if s.step_id == step_id), None)
        
        if step:
            instance.total_cost += step.cost
            instance.quality_score *= step.quality_impact
            
            # Check for failure
            if random.random() < step.failure_rate:
                instance.failed_steps.append(step_id)
                instance.status = ProcessStatus.FAILED
                return
            
            # Schedule next steps
            next_steps = await self._find_next_steps(process, step_id, instance.completed_steps)
            for next_step_id in next_steps:
                await self._schedule_step(instance, next_step_id, scenario, mode)
    
    async def _simulate_step_duration(self, step: ProcessStep, mode: SimulationMode) -> float:
        """Simulate step duration based on distribution and mode"""
        if mode == SimulationMode.DETERMINISTIC:
            return (step.duration_min + step.duration_max) / 2
        
        elif mode == SimulationMode.STOCHASTIC or mode == SimulationMode.MONTE_CARLO:
            if step.duration_distribution == "normal":
                mean = (step.duration_min + step.duration_max) / 2
                std = (step.duration_max - step.duration_min) / 4
                return max(step.duration_min, np.random.normal(mean, std))
            
            elif step.duration_distribution == "uniform":
                return np.random.uniform(step.duration_min, step.duration_max)
            
            elif step.duration_distribution == "exponential":
                rate = 1.0 / ((step.duration_min + step.duration_max) / 2)
                return np.random.exponential(1.0 / rate)
        
        # Default to uniform distribution
        return np.random.uniform(step.duration_min, step.duration_max)
    
    async def _get_process_definition(self, process_id: str, scenario: SimulationScenario) -> Optional[BusinessProcess]:
        """Get process definition (simplified - would come from database)"""
        # This would typically fetch from a process repository
        # For simulation, we'll create a sample process
        if process_id in scenario.processes:
            return BusinessProcess(
                process_id=process_id,
                name=f"Process {process_id}",
                description=f"Sample process {process_id}",
                steps=[
                    ProcessStep(
                        step_id=f"{process_id}_step1",
                        name="Initial Step",
                        description="First step",
                        required_resources=[("human_resource", 1.0)],
                        duration_min=30.0,
                        duration_max=60.0,
                        cost=50.0
                    ),
                    ProcessStep(
                        step_id=f"{process_id}_step2",
                        name="Processing Step",
                        description="Main processing",
                        required_resources=[("equipment_resource", 1.0)],
                        duration_min=60.0,
                        duration_max=120.0,
                        cost=100.0,
                        dependencies=[f"{process_id}_step1"]
                    ),
                    ProcessStep(
                        step_id=f"{process_id}_step3",
                        name="Final Step",
                        description="Completion step",
                        required_resources=[("human_resource", 1.0)],
                        duration_min=15.0,
                        duration_max=30.0,
                        cost=25.0,
                        dependencies=[f"{process_id}_step2"]
                    )
                ]
            )
        return None
    
    async def _find_first_steps(self, process: BusinessProcess) -> List[str]:
        """Find steps with no dependencies"""
        first_steps = []
        for step in process.steps:
            if not step.dependencies:
                first_steps.append(step.step_id)
        return first_steps
    
    async def _find_next_steps(self, process: BusinessProcess, completed_step_id: str, 
                             all_completed: List[str]) -> List[str]:
        """Find steps that can now be executed"""
        next_steps = []
        
        for step in process.steps:
            if step.step_id not in all_completed:
                # Check if all dependencies are satisfied
                dependencies_met = all(dep in all_completed for dep in step.dependencies)
                if dependencies_met:
                    next_steps.append(step.step_id)
        
        return next_steps
    
    async def _is_process_complete(self, instance: ProcessInstance, scenario: SimulationScenario) -> bool:
        """Check if process instance is complete"""
        process = await self._get_process_definition(instance.process_id, scenario)
        if process:
            all_step_ids = {step.step_id for step in process.steps}
            completed_step_ids = set(instance.completed_steps)
            return all_step_ids.issubset(completed_step_ids)
        return False
    
    async def _analyze_results(self, scenario: SimulationScenario, instances: List[ProcessInstance], 
                             mode: SimulationMode) -> SimulationResult:
        """Analyze simulation results"""
        total_processes = len(instances)
        completed_processes = len([i for i in instances if i.status == ProcessStatus.COMPLETED])
        failed_processes = len([i for i in instances if i.status == ProcessStatus.FAILED])
        
        # Calculate completion times
        completion_times = []
        for instance in instances:
            if instance.status == ProcessStatus.COMPLETED and instance.completed_at:
                completion_time = (instance.completed_at - instance.started_at).total_seconds() / 3600.0
                completion_times.append(completion_time)
        
        average_completion_time = statistics.mean(completion_times) if completion_times else 0.0
        
        # Calculate total cost
        total_cost = sum(instance.total_cost for instance in instances)
        
        # Calculate throughput
        throughput = completed_processes / scenario.simulation_duration if scenario.simulation_duration > 0 else 0
        
        # Identify bottlenecks (simplified)
        bottlenecks = await self._identify_bottlenecks(instances, scenario)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(instances, scenario)
        
        return SimulationResult(
            result_id=str(uuid4()),
            scenario_id=scenario.scenario_id,
            mode=mode,
            total_processes=total_processes,
            completed_processes=completed_processes,
            failed_processes=failed_processes,
            average_completion_time=average_completion_time,
            total_cost=total_cost,
            resource_utilization={},  # Would calculate from resource usage
            bottlenecks=bottlenecks,
            quality_metrics={'average_quality': statistics.mean([i.quality_score for i in instances]) if instances else 0.0},
            throughput=throughput,
            cycle_time=average_completion_time,
            wait_time=0.0,  # Would calculate from waiting times
            process_efficiency=completed_processes / total_processes if total_processes > 0 else 0.0,
            sla_compliance=0.8,  # Would calculate based on SLA requirements
            recommendations=recommendations
        )
    
    async def _identify_bottlenecks(self, instances: List[ProcessInstance], 
                                  scenario: SimulationScenario) -> List[Tuple[str, str, float]]:
        """Identify process bottlenecks"""
        bottlenecks = []
        
        # Analyze step durations
        step_durations = {}
        for instance in instances:
            for step_id in instance.completed_steps:
                if step_id in instance.step_start_times and step_id in instance.step_end_times:
                    duration = (instance.step_end_times[step_id] - instance.step_start_times[step_id]).total_seconds() / 60.0
                    if step_id not in step_durations:
                        step_durations[step_id] = []
                    step_durations[step_id].append(duration)
        
        # Find steps with high average duration
        for step_id, durations in step_durations.items():
            avg_duration = statistics.mean(durations)
            if avg_duration > 120:  # More than 2 hours
                severity = min(avg_duration / 60, 10.0)  # Scale to 0-10
                bottlenecks.append((step_id, "step_duration", severity))
        
        return bottlenecks
    
    async def _generate_recommendations(self, instances: List[ProcessInstance], 
                                      scenario: SimulationScenario) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Analyze failure rates
        failed_instances = len([i for i in instances if i.status == ProcessStatus.FAILED])
        if failed_instances > 0:
            failure_rate = failed_instances / len(instances)
            if failure_rate > 0.1:
                recommendations.append(f"High failure rate ({failure_rate:.1%}) - review process steps for quality issues")
        
        # Analyze completion times
        completed_instances = [i for i in instances if i.status == ProcessStatus.COMPLETED]
        if completed_instances:
            completion_times = []
            for instance in completed_instances:
                if instance.completed_at:
                    time_hours = (instance.completed_at - instance.started_at).total_seconds() / 3600.0
                    completion_times.append(time_hours)
            
            if completion_times:
                avg_time = statistics.mean(completion_times)
                if avg_time > 8:  # More than 8 hours
                    recommendations.append(f"Average completion time is {avg_time:.1f} hours - consider process optimization")
        
        # Analyze costs
        if instances:
            avg_cost = sum(i.total_cost for i in instances) / len(instances)
            if avg_cost > 1000:
                recommendations.append(f"High average cost per process (${avg_cost:.2f}) - review resource allocation")
        
        return recommendations
    
    # Optimization suggestion methods
    
    async def _analyze_current_process(self, process: BusinessProcess) -> Dict[str, float]:
        """Analyze current process performance"""
        metrics = {}
        
        # Calculate theoretical metrics
        total_min_duration = sum(step.duration_min for step in process.steps)
        total_max_duration = sum(step.duration_max for step in process.steps)
        total_cost = sum(step.cost for step in process.steps)
        
        metrics['min_duration'] = total_min_duration
        metrics['max_duration'] = total_max_duration
        metrics['expected_duration'] = (total_min_duration + total_max_duration) / 2
        metrics['total_cost'] = total_cost
        metrics['step_count'] = len(process.steps)
        
        # Analyze complexity
        parallel_opportunities = 0
        for step in process.steps:
            if step.parallel_steps:
                parallel_opportunities += len(step.parallel_steps)
        
        metrics['parallel_opportunities'] = parallel_opportunities
        metrics['complexity_score'] = len(process.steps) + len([s for s in process.steps if s.dependencies])
        
        return metrics
    
    async def _suggest_resource_optimizations(self, process: BusinessProcess, 
                                            metrics: Dict[str, float]) -> List[OptimizationSuggestion]:
        """Suggest resource-based optimizations"""
        suggestions = []
        
        # Analyze resource requirements
        resource_usage = {}
        for step in process.steps:
            for resource_id, quantity in step.required_resources:
                if resource_id not in resource_usage:
                    resource_usage[resource_id] = 0
                resource_usage[resource_id] += quantity
        
        # Suggest resource consolidation
        if len(resource_usage) > 5:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="resource_consolidation",
                description="Consider consolidating resource types to reduce complexity",
                expected_impact={'efficiency': 0.15, 'cost_reduction': 0.10},
                implementation_cost=5000.0,
                implementation_time=30.0,
                confidence=0.7,
                affected_processes=[process.process_id],
                affected_resources=list(resource_usage.keys()),
                priority=3
            ))
        
        # Suggest parallel resource allocation
        if metrics.get('parallel_opportunities', 0) > 0:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="parallel_resources",
                description="Add parallel resource allocation to reduce completion time",
                expected_impact={'time_reduction': 0.25, 'throughput_increase': 0.30},
                implementation_cost=10000.0,
                implementation_time=45.0,
                confidence=0.8,
                affected_processes=[process.process_id],
                affected_resources=list(resource_usage.keys()),
                priority=2
            ))
        
        return suggestions
    
    async def _suggest_flow_optimizations(self, process: BusinessProcess, 
                                        metrics: Dict[str, float]) -> List[OptimizationSuggestion]:
        """Suggest process flow optimizations"""
        suggestions = []
        
        # Suggest step reordering
        if metrics.get('step_count', 0) > 5:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="step_reordering",
                description="Reorder steps to minimize dependencies and enable parallelization",
                expected_impact={'time_reduction': 0.20, 'efficiency': 0.15},
                implementation_cost=2000.0,
                implementation_time=14.0,
                confidence=0.6,
                affected_processes=[process.process_id],
                affected_resources=[],
                priority=3
            ))
        
        # Suggest step elimination
        non_critical_steps = [step for step in process.steps if not step.dependencies and step.cost < 50]
        if len(non_critical_steps) > 1:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="step_elimination",
                description="Consider eliminating or combining low-value steps",
                expected_impact={'time_reduction': 0.15, 'cost_reduction': 0.20},
                implementation_cost=1000.0,
                implementation_time=7.0,
                confidence=0.7,
                affected_processes=[process.process_id],
                affected_resources=[],
                priority=4
            ))
        
        return suggestions
    
    async def _suggest_scheduling_optimizations(self, process: BusinessProcess, 
                                              metrics: Dict[str, float]) -> List[OptimizationSuggestion]:
        """Suggest scheduling optimizations"""
        suggestions = []
        
        # Suggest batching
        if metrics.get('step_count', 0) > 3:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="batch_processing",
                description="Implement batch processing for similar steps",
                expected_impact={'efficiency': 0.25, 'resource_utilization': 0.30},
                implementation_cost=3000.0,
                implementation_time=21.0,
                confidence=0.8,
                affected_processes=[process.process_id],
                affected_resources=[],
                priority=2
            ))
        
        # Suggest priority-based scheduling
        suggestions.append(OptimizationSuggestion(
            suggestion_id=str(uuid4()),
            type="priority_scheduling",
            description="Implement priority-based scheduling system",
            expected_impact={'sla_compliance': 0.20, 'customer_satisfaction': 0.15},
            implementation_cost=8000.0,
            implementation_time=60.0,
            confidence=0.9,
            affected_processes=[process.process_id],
            affected_resources=[],
            priority=1
        ))
        
        return suggestions
    
    async def _suggest_quality_optimizations(self, process: BusinessProcess, 
                                           metrics: Dict[str, float]) -> List[OptimizationSuggestion]:
        """Suggest quality optimizations"""
        suggestions = []
        
        # Analyze failure rates
        high_failure_steps = [step for step in process.steps if step.failure_rate > 0.05]
        if high_failure_steps:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="quality_improvement",
                description="Implement quality controls for high-failure steps",
                expected_impact={'failure_reduction': 0.50, 'quality_score': 0.20},
                implementation_cost=15000.0,
                implementation_time=90.0,
                confidence=0.8,
                affected_processes=[process.process_id],
                affected_resources=[],
                priority=1
            ))
        
        # Suggest quality checkpoints
        if len(process.steps) > 4:
            suggestions.append(OptimizationSuggestion(
                suggestion_id=str(uuid4()),
                type="quality_checkpoints",
                description="Add quality checkpoints between major process phases",
                expected_impact={'quality_score': 0.15, 'rework_reduction': 0.30},
                implementation_cost=5000.0,
                implementation_time=30.0,
                confidence=0.7,
                affected_processes=[process.process_id],
                affected_resources=[],
                priority=3
            ))
        
        return suggestions


class IntelligentResourceManager(ResourceManager):
    """Intelligent resource allocation and management"""
    
    def __init__(self):
        self.resource_pool = {}
        self.allocation_history = []
        self.utilization_metrics = {}
    
    async def allocate_resources(self, step: ProcessStep, instance: ProcessInstance, 
                               available_resources: List[Resource]) -> List[Resource]:
        """Intelligent resource allocation based on requirements and availability"""
        try:
            allocated = []
            
            for resource_type_id, required_quantity in step.required_resources:
                # Find matching resources
                matching_resources = [
                    r for r in available_resources 
                    if r.resource_id == resource_type_id or r.resource_type.value in resource_type_id
                ]
                
                # Sort by efficiency and availability
                matching_resources.sort(key=lambda r: (r.efficiency_factor, -r.utilization_rate), reverse=True)
                
                # Allocate best resources
                allocated_quantity = 0
                for resource in matching_resources:
                    if allocated_quantity >= required_quantity:
                        break
                    
                    available_capacity = resource.capacity * (1 - resource.utilization_rate)
                    if available_capacity > 0:
                        allocation_amount = min(available_capacity, required_quantity - allocated_quantity)
                        allocated.append(resource)
                        allocated_quantity += allocation_amount
                        
                        # Update utilization
                        resource.utilization_rate += allocation_amount / resource.capacity
            
            # Record allocation
            self.allocation_history.append({
                'step_id': step.step_id,
                'instance_id': instance.instance_id,
                'resources': [r.resource_id for r in allocated],
                'timestamp': datetime.now()
            })
            
            return allocated
            
        except Exception as e:
            logger.error(f"Error allocating resources: {e}")
            return []
    
    async def release_resources(self, resources: List[Resource], instance: ProcessInstance) -> None:
        """Release resources after step completion"""
        try:
            for resource in resources:
                # Reset utilization (simplified)
                resource.utilization_rate = max(0, resource.utilization_rate - 0.1)
                
                # Update metrics
                if resource.resource_id not in self.utilization_metrics:
                    self.utilization_metrics[resource.resource_id] = []
                
                self.utilization_metrics[resource.resource_id].append({
                    'utilization': resource.utilization_rate,
                    'timestamp': datetime.now(),
                    'instance_id': instance.instance_id
                })
            
        except Exception as e:
            logger.error(f"Error releasing resources: {e}")
    
    async def get_utilization_report(self) -> Dict[str, Dict[str, float]]:
        """Generate resource utilization report"""
        report = {}
        
        for resource_id, metrics in self.utilization_metrics.items():
            if metrics:
                utilizations = [m['utilization'] for m in metrics]
                report[resource_id] = {
                    'average_utilization': statistics.mean(utilizations),
                    'max_utilization': max(utilizations),
                    'min_utilization': min(utilizations),
                    'utilization_variance': statistics.variance(utilizations) if len(utilizations) > 1 else 0
                }
        
        return report


class AdvancedProcessAnalyzer(ProcessAnalyzer):
    """Advanced process analysis using machine learning"""
    
    def __init__(self):
        self.bottleneck_model = None
        self.performance_model = None
        self.historical_data = []
    
    async def analyze_bottlenecks(self, results: List[SimulationResult]) -> List[Tuple[str, str, float]]:
        """Advanced bottleneck analysis"""
        try:
            bottlenecks = []
            
            # Aggregate bottleneck data across results
            bottleneck_counts = {}
            bottleneck_severities = {}
            
            for result in results:
                for bottleneck_id, bottleneck_type, severity in result.bottlenecks:
                    key = (bottleneck_id, bottleneck_type)
                    
                    if key not in bottleneck_counts:
                        bottleneck_counts[key] = 0
                        bottleneck_severities[key] = []
                    
                    bottleneck_counts[key] += 1
                    bottleneck_severities[key].append(severity)
            
            # Rank bottlenecks by frequency and severity
            for (bottleneck_id, bottleneck_type), count in bottleneck_counts.items():
                avg_severity = statistics.mean(bottleneck_severities[(bottleneck_id, bottleneck_type)])
                combined_score = count * avg_severity
                bottlenecks.append((bottleneck_id, bottleneck_type, combined_score))
            
            # Sort by combined score
            bottlenecks.sort(key=lambda x: x[2], reverse=True)
            
            return bottlenecks[:10]  # Return top 10 bottlenecks
            
        except Exception as e:
            logger.error(f"Error analyzing bottlenecks: {e}")
            return []
    
    async def predict_performance(self, process: BusinessProcess, resources: List[Resource]) -> Dict[str, float]:
        """Predict process performance using ML models"""
        try:
            # Feature extraction
            features = await self._extract_features(process, resources)
            
            # Simple prediction model (in production, use trained ML model)
            predicted_metrics = {}
            
            # Predict completion time
            base_time = sum((step.duration_min + step.duration_max) / 2 for step in process.steps)
            complexity_factor = 1 + (len(process.steps) * 0.1)
            resource_factor = max(0.5, min(2.0, len(resources) / 10))
            
            predicted_metrics['completion_time'] = base_time * complexity_factor / resource_factor
            
            # Predict cost
            base_cost = sum(step.cost for step in process.steps)
            resource_cost = sum(r.cost_per_hour for r in resources) * (predicted_metrics['completion_time'] / 60)
            predicted_metrics['total_cost'] = base_cost + resource_cost
            
            # Predict quality
            quality_factors = [step.quality_impact for step in process.steps]
            predicted_metrics['quality_score'] = np.prod(quality_factors) if quality_factors else 1.0
            
            # Predict throughput
            predicted_metrics['throughput'] = 60 / predicted_metrics['completion_time']  # processes per hour
            
            return predicted_metrics
            
        except Exception as e:
            logger.error(f"Error predicting performance: {e}")
            return {}
    
    async def _extract_features(self, process: BusinessProcess, resources: List[Resource]) -> np.ndarray:
        """Extract features for ML models"""
        features = []
        
        # Process features
        features.extend([
            len(process.steps),
            sum(len(step.dependencies) for step in process.steps),
            sum(step.cost for step in process.steps),
            sum(step.duration_max for step in process.steps),
            sum(step.failure_rate for step in process.steps),
            process.priority.value
        ])
        
        # Resource features
        if resources:
            features.extend([
                len(resources),
                sum(r.capacity for r in resources),
                statistics.mean(r.cost_per_hour for r in resources),
                statistics.mean(r.efficiency_factor for r in resources),
                statistics.mean(r.skill_level for r in resources)
            ])
        else:
            features.extend([0, 0, 0, 1, 1])  # Default values
        
        return np.array(features)


class BusinessProcessSimulationService:
    """Main business process simulation service"""
    
    def __init__(self,
                 simulator: ProcessSimulator,
                 resource_manager: ResourceManager,
                 analyzer: ProcessAnalyzer):
        self.simulator = simulator
        self.resource_manager = resource_manager
        self.analyzer = analyzer
        
        # Storage
        self.processes: Dict[str, BusinessProcess] = {}
        self.resources: Dict[str, Resource] = {}
        self.scenarios: Dict[str, SimulationScenario] = {}
        self.results: Dict[str, SimulationResult] = {}
        self.optimizations: Dict[str, List[OptimizationSuggestion]] = {}
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the simulation service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Business Process Simulation Service")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._monitor_simulation_queue()),
            asyncio.create_task(self._generate_optimization_reports()),
            asyncio.create_task(self._update_performance_models())
        ]
    
    async def stop(self):
        """Stop the simulation service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Business Process Simulation Service")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def create_process(self, process: BusinessProcess) -> bool:
        """Register a business process"""
        try:
            self.processes[process.process_id] = process
            logger.info(f"Registered process: {process.name}")
            return True
        except Exception as e:
            logger.error(f"Error creating process: {e}")
            return False
    
    async def create_scenario(self, scenario: SimulationScenario) -> bool:
        """Create a simulation scenario"""
        try:
            self.scenarios[scenario.scenario_id] = scenario
            logger.info(f"Created scenario: {scenario.name}")
            return True
        except Exception as e:
            logger.error(f"Error creating scenario: {e}")
            return False
    
    async def run_simulation(self, scenario_id: str, mode: SimulationMode = SimulationMode.STOCHASTIC) -> Optional[SimulationResult]:
        """Run a simulation"""
        try:
            if scenario_id not in self.scenarios:
                logger.warning(f"Scenario {scenario_id} not found")
                return None
            
            scenario = self.scenarios[scenario_id]
            result = await self.simulator.simulate(scenario, mode)
            
            # Store result
            self.results[result.result_id] = result
            
            logger.info(f"Completed simulation {result.result_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            return None
    
    async def optimize_process(self, process_id: str, constraints: Dict[str, Any] = None) -> List[OptimizationSuggestion]:
        """Optimize a business process"""
        try:
            if process_id not in self.processes:
                logger.warning(f"Process {process_id} not found")
                return []
            
            if constraints is None:
                constraints = {}
            
            process = self.processes[process_id]
            suggestions = await self.simulator.optimize_process(process, constraints)
            
            # Store optimizations
            self.optimizations[process_id] = suggestions
            
            logger.info(f"Generated {len(suggestions)} optimization suggestions for process {process_id}")
            return suggestions
            
        except Exception as e:
            logger.error(f"Error optimizing process: {e}")
            return []
    
    async def get_performance_prediction(self, process_id: str) -> Dict[str, float]:
        """Get performance prediction for a process"""
        try:
            if process_id not in self.processes:
                return {}
            
            process = self.processes[process_id]
            available_resources = list(self.resources.values())
            
            prediction = await self.analyzer.predict_performance(process, available_resources)
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error getting performance prediction: {e}")
            return {}
    
    async def compare_scenarios(self, scenario_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple simulation scenarios"""
        try:
            comparison = {}
            
            scenario_results = []
            for scenario_id in scenario_ids:
                # Run simulation if not already done
                if scenario_id not in [r.scenario_id for r in self.results.values()]:
                    result = await self.run_simulation(scenario_id)
                    if result:
                        scenario_results.append(result)
                else:
                    # Find existing result
                    result = next((r for r in self.results.values() if r.scenario_id == scenario_id), None)
                    if result:
                        scenario_results.append(result)
            
            if len(scenario_results) < 2:
                return {"error": "Need at least 2 scenarios for comparison"}
            
            # Compare metrics
            comparison["scenarios"] = len(scenario_results)
            comparison["metrics"] = {}
            
            metrics = ["average_completion_time", "total_cost", "throughput", "process_efficiency"]
            
            for metric in metrics:
                values = [getattr(result, metric, 0) for result in scenario_results]
                comparison["metrics"][metric] = {
                    "values": values,
                    "best": min(values) if metric in ["average_completion_time", "total_cost"] else max(values),
                    "worst": max(values) if metric in ["average_completion_time", "total_cost"] else min(values),
                    "average": statistics.mean(values),
                    "variance": statistics.variance(values) if len(values) > 1 else 0
                }
            
            # Identify best scenario
            best_scenario_idx = 0
            best_score = 0
            
            for i, result in enumerate(scenario_results):
                # Simple scoring (lower time and cost, higher throughput and efficiency is better)
                score = (
                    (1 / result.average_completion_time if result.average_completion_time > 0 else 0) * 0.25 +
                    (1 / result.total_cost if result.total_cost > 0 else 0) * 0.25 +
                    result.throughput * 0.25 +
                    result.process_efficiency * 0.25
                )
                
                if score > best_score:
                    best_score = score
                    best_scenario_idx = i
            
            comparison["best_scenario"] = {
                "scenario_id": scenario_results[best_scenario_idx].scenario_id,
                "score": best_score
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing scenarios: {e}")
            return {"error": str(e)}
    
    async def get_simulation_summary(self) -> Dict[str, Any]:
        """Get summary of all simulations"""
        try:
            summary = {
                "total_processes": len(self.processes),
                "total_scenarios": len(self.scenarios),
                "total_simulations": len(self.results),
                "total_resources": len(self.resources)
            }
            
            if self.results:
                results_list = list(self.results.values())
                
                summary["simulation_metrics"] = {
                    "average_completion_time": statistics.mean(r.average_completion_time for r in results_list),
                    "average_cost": statistics.mean(r.total_cost for r in results_list),
                    "average_throughput": statistics.mean(r.throughput for r in results_list),
                    "average_efficiency": statistics.mean(r.process_efficiency for r in results_list)
                }
                
                # Most recent simulation
                most_recent = max(results_list, key=lambda x: x.executed_at)
                summary["most_recent_simulation"] = {
                    "result_id": most_recent.result_id,
                    "scenario_id": most_recent.scenario_id,
                    "executed_at": most_recent.executed_at.isoformat(),
                    "completion_time": most_recent.average_completion_time,
                    "efficiency": most_recent.process_efficiency
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting simulation summary: {e}")
            return {}
    
    # Background tasks
    
    async def _monitor_simulation_queue(self):
        """Monitor simulation queue and process requests"""
        while self._running:
            try:
                # In a real implementation, this would process queued simulations
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in simulation queue monitor: {e}")
                await asyncio.sleep(300)
    
    async def _generate_optimization_reports(self):
        """Generate periodic optimization reports"""
        while self._running:
            try:
                # Generate reports for processes with recent simulations
                for process_id in self.processes.keys():
                    if process_id not in self.optimizations:
                        await self.optimize_process(process_id)
                
                logger.info("Generated optimization reports")
                
                # Wait 24 hours before next report generation
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating optimization reports: {e}")
                await asyncio.sleep(86400)
    
    async def _update_performance_models(self):
        """Update performance prediction models with new data"""
        while self._running:
            try:
                # In a real implementation, this would retrain ML models
                # with new simulation data
                
                if len(self.results) > 100:  # Enough data for model update
                    logger.info("Performance models would be updated with new data")
                
                # Wait 7 days before next model update
                await asyncio.sleep(604800)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error updating performance models: {e}")
                await asyncio.sleep(604800)


# Singleton instance
_business_process_simulation_service: Optional[BusinessProcessSimulationService] = None


def get_business_process_simulation_service() -> BusinessProcessSimulationService:
    """Get the singleton business process simulation service instance"""
    global _business_process_simulation_service
    
    if _business_process_simulation_service is None:
        # Initialize with default implementations
        simulator = DiscreteEventSimulator()
        resource_manager = IntelligentResourceManager()
        analyzer = AdvancedProcessAnalyzer()
        
        _business_process_simulation_service = BusinessProcessSimulationService(
            simulator=simulator,
            resource_manager=resource_manager,
            analyzer=analyzer
        )
    
    return _business_process_simulation_service


async def main():
    """Example usage of the business process simulation service"""
    service = get_business_process_simulation_service()
    
    try:
        await service.start()
        
        # Example 1: Create a business process
        print("=== Creating Business Process ===")
        
        process = BusinessProcess(
            process_id="order_fulfillment",
            name="Order Fulfillment Process",
            description="Complete order processing from receipt to delivery",
            steps=[
                ProcessStep(
                    step_id="receive_order",
                    name="Receive Order",
                    description="Process incoming order",
                    required_resources=[("customer_service", 1.0)],
                    duration_min=5.0,
                    duration_max=15.0,
                    cost=25.0
                ),
                ProcessStep(
                    step_id="check_inventory",
                    name="Check Inventory",
                    description="Verify product availability",
                    required_resources=[("inventory_system", 1.0)],
                    duration_min=2.0,
                    duration_max=5.0,
                    cost=10.0,
                    dependencies=["receive_order"]
                ),
                ProcessStep(
                    step_id="process_payment",
                    name="Process Payment",
                    description="Handle payment processing",
                    required_resources=[("payment_system", 1.0)],
                    duration_min=3.0,
                    duration_max=10.0,
                    cost=15.0,
                    dependencies=["check_inventory"]
                ),
                ProcessStep(
                    step_id="pick_pack",
                    name="Pick and Pack",
                    description="Prepare order for shipping",
                    required_resources=[("warehouse_staff", 1.0)],
                    duration_min=15.0,
                    duration_max=45.0,
                    cost=75.0,
                    dependencies=["process_payment"]
                ),
                ProcessStep(
                    step_id="ship_order",
                    name="Ship Order",
                    description="Ship order to customer",
                    required_resources=[("shipping_system", 1.0)],
                    duration_min=5.0,
                    duration_max=10.0,
                    cost=50.0,
                    dependencies=["pick_pack"]
                )
            ],
            priority=ProcessPriority.HIGH,
            sla_hours=24.0
        )
        
        success = await service.create_process(process)
        print(f"Created process: {success}")
        
        # Example 2: Create simulation scenario
        print("=== Creating Simulation Scenario ===")
        
        scenario = SimulationScenario(
            scenario_id="peak_hours_scenario",
            name="Peak Hours Load Test",
            description="Simulate high order volume during peak hours",
            processes=["order_fulfillment"],
            resources=["customer_service", "inventory_system", "payment_system", "warehouse_staff", "shipping_system"],
            simulation_duration=8.0,  # 8 hours
            arrival_rate=5.0,  # 5 orders per hour
            arrival_pattern="poisson",
            objectives=["minimize_cost", "maximize_throughput", "meet_sla"]
        )
        
        success = await service.create_scenario(scenario)
        print(f"Created scenario: {success}")
        
        # Example 3: Run simulation
        print("=== Running Simulation ===")
        
        result = await service.run_simulation("peak_hours_scenario", SimulationMode.MONTE_CARLO)
        
        if result:
            print(f"Simulation completed:")
            print(f"  Total processes: {result.total_processes}")
            print(f"  Completed: {result.completed_processes}")
            print(f"  Failed: {result.failed_processes}")
            print(f"  Average completion time: {result.average_completion_time:.2f} hours")
            print(f"  Total cost: ${result.total_cost:.2f}")
            print(f"  Throughput: {result.throughput:.2f} processes/hour")
            print(f"  Process efficiency: {result.process_efficiency:.2%}")
            print(f"  SLA compliance: {result.sla_compliance:.2%}")
            
            if result.bottlenecks:
                print(f"  Bottlenecks identified: {len(result.bottlenecks)}")
                for bottleneck_id, bottleneck_type, severity in result.bottlenecks[:3]:
                    print(f"    - {bottleneck_id} ({bottleneck_type}): severity {severity:.2f}")
            
            if result.recommendations:
                print(f"  Recommendations: {len(result.recommendations)}")
                for rec in result.recommendations[:3]:
                    print(f"    - {rec}")
        
        # Example 4: Get optimization suggestions
        print("\n=== Process Optimization ===")
        
        optimizations = await service.optimize_process("order_fulfillment")
        
        if optimizations:
            print(f"Generated {len(optimizations)} optimization suggestions:")
            
            for opt in optimizations[:3]:
                print(f"\nSuggestion: {opt.type}")
                print(f"  Description: {opt.description}")
                print(f"  Expected impact: {opt.expected_impact}")
                print(f"  Implementation cost: ${opt.implementation_cost:.2f}")
                print(f"  Implementation time: {opt.implementation_time} days")
                print(f"  Confidence: {opt.confidence:.2%}")
                print(f"  Priority: {opt.priority}/5")
        
        # Example 5: Performance prediction
        print("\n=== Performance Prediction ===")
        
        prediction = await service.get_performance_prediction("order_fulfillment")
        
        if prediction:
            print("Performance predictions:")
            for metric, value in prediction.items():
                if isinstance(value, float):
                    if 'time' in metric:
                        print(f"  {metric}: {value:.2f} minutes")
                    elif 'cost' in metric:
                        print(f"  {metric}: ${value:.2f}")
                    elif 'score' in metric:
                        print(f"  {metric}: {value:.2f}")
                    else:
                        print(f"  {metric}: {value:.2f}")
                else:
                    print(f"  {metric}: {value}")
        
        # Example 6: Simulation summary
        print("\n=== Simulation Summary ===")
        
        summary = await service.get_simulation_summary()
        
        if summary:
            print(f"Total processes: {summary.get('total_processes', 0)}")
            print(f"Total scenarios: {summary.get('total_scenarios', 0)}")
            print(f"Total simulations: {summary.get('total_simulations', 0)}")
            
            if 'simulation_metrics' in summary:
                metrics = summary['simulation_metrics']
                print("\nAverage simulation metrics:")
                print(f"  Completion time: {metrics.get('average_completion_time', 0):.2f} hours")
                print(f"  Cost: ${metrics.get('average_cost', 0):.2f}")
                print(f"  Throughput: {metrics.get('average_throughput', 0):.2f} processes/hour")
                print(f"  Efficiency: {metrics.get('average_efficiency', 0):.2%}")
        
        # Let background tasks run briefly
        await asyncio.sleep(5)
        
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())