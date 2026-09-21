#!/usr/bin/env python3
"""
Batch Job Optimizer for ActiveLog Compute Tiers
Intelligent optimization of AWS Batch jobs for cost and performance
"""

import boto3
import json
import logging
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OptimizationGoal(Enum):
    """Optimization goals for batch jobs"""
    COST = "cost"
    TIME = "time"
    BALANCED = "balanced"
    THROUGHPUT = "throughput"
    RELIABILITY = "reliability"

class JobType(Enum):
    """Types of batch jobs"""
    CPU_INTENSIVE = "cpu_intensive"
    MEMORY_INTENSIVE = "memory_intensive"
    IO_INTENSIVE = "io_intensive"
    NETWORK_INTENSIVE = "network_intensive"
    GPU_COMPUTE = "gpu_compute"
    MIXED_WORKLOAD = "mixed_workload"

@dataclass
class BatchJobSpec:
    """Batch job specification"""
    job_name: str
    job_queue: str
    job_definition: str
    job_type: JobType
    vcpus: int
    memory_mb: int
    gpu_count: int
    estimated_runtime_minutes: int
    priority: int
    retry_attempts: int
    timeout_minutes: Optional[int]
    depends_on: List[str]
    parameters: Dict[str, Any]

@dataclass
class OptimizationRecommendation:
    """Batch job optimization recommendation"""
    job_name: str
    current_config: Dict[str, Any]
    recommended_config: Dict[str, Any]
    optimization_type: str
    estimated_cost_savings: float
    estimated_time_savings: float
    confidence_score: float
    implementation_notes: str

class BatchOptimizer:
    """Optimizes AWS Batch job configurations and execution"""
    
    def __init__(self, batch_client, ec2_client):
        self.batch = batch_client
        self.ec2 = ec2_client
        
        # Instance type specifications for batch compute
        self.compute_instances = {
            # CPU Optimized
            'c5.large': {'vcpus': 2, 'memory': 4096, 'cost_per_hour': 0.085, 'network': 'up_to_10gb'},
            'c5.xlarge': {'vcpus': 4, 'memory': 8192, 'cost_per_hour': 0.17, 'network': 'up_to_10gb'},
            'c5.2xlarge': {'vcpus': 8, 'memory': 16384, 'cost_per_hour': 0.34, 'network': 'up_to_10gb'},
            'c5.4xlarge': {'vcpus': 16, 'memory': 32768, 'cost_per_hour': 0.68, 'network': 'up_to_10gb'},
            'c5.9xlarge': {'vcpus': 36, 'memory': 73728, 'cost_per_hour': 1.53, 'network': '10gb'},
            'c5.18xlarge': {'vcpus': 72, 'memory': 147456, 'cost_per_hour': 3.06, 'network': '25gb'},
            
            # Memory Optimized
            'r5.large': {'vcpus': 2, 'memory': 16384, 'cost_per_hour': 0.126, 'network': 'up_to_10gb'},
            'r5.xlarge': {'vcpus': 4, 'memory': 32768, 'cost_per_hour': 0.252, 'network': 'up_to_10gb'},
            'r5.2xlarge': {'vcpus': 8, 'memory': 65536, 'cost_per_hour': 0.504, 'network': 'up_to_10gb'},
            'r5.4xlarge': {'vcpus': 16, 'memory': 131072, 'cost_per_hour': 1.008, 'network': 'up_to_10gb'},
            'r5.8xlarge': {'vcpus': 32, 'memory': 262144, 'cost_per_hour': 2.016, 'network': '10gb'},
            'r5.16xlarge': {'vcpus': 64, 'memory': 524288, 'cost_per_hour': 4.032, 'network': '20gb'},
            
            # General Purpose
            'm5.large': {'vcpus': 2, 'memory': 8192, 'cost_per_hour': 0.096, 'network': 'up_to_10gb'},
            'm5.xlarge': {'vcpus': 4, 'memory': 16384, 'cost_per_hour': 0.192, 'network': 'up_to_10gb'},
            'm5.2xlarge': {'vcpus': 8, 'memory': 32768, 'cost_per_hour': 0.384, 'network': 'up_to_10gb'},
            'm5.4xlarge': {'vcpus': 16, 'memory': 65536, 'cost_per_hour': 0.768, 'network': 'up_to_10gb'},
            'm5.8xlarge': {'vcpus': 32, 'memory': 131072, 'cost_per_hour': 1.536, 'network': '10gb'},
            'm5.16xlarge': {'vcpus': 64, 'memory': 262144, 'cost_per_hour': 3.072, 'network': '20gb'},
        }
        
        # Spot pricing discounts (approximate)
        self.spot_discounts = {
            'c5': 0.65,  # 65% of on-demand price
            'r5': 0.70,
            'm5': 0.68
        }
        
        # Job type to instance family mapping
        self.job_type_instances = {
            JobType.CPU_INTENSIVE: ['c5', 'c5n'],
            JobType.MEMORY_INTENSIVE: ['r5', 'r5a', 'x1e'],
            JobType.IO_INTENSIVE: ['i3', 'i3en', 'd2'],
            JobType.NETWORK_INTENSIVE: ['c5n', 'm5n', 'r5n'],
            JobType.GPU_COMPUTE: ['p3', 'p4', 'g4dn'],
            JobType.MIXED_WORKLOAD: ['m5', 'm5a', 'm5n']
        }

    def optimize_jobs(self, job_queue: str, optimization_goals: List[str]) -> Dict[str, Any]:
        """Optimize batch jobs in a queue based on specified goals"""
        try:
            goals = [OptimizationGoal(goal) for goal in optimization_goals]
            
            # Get current job definitions and queue configuration
            job_definitions = self._get_job_definitions(job_queue)
            queue_config = self._get_queue_configuration(job_queue)
            
            optimization_result = {
                'timestamp': datetime.utcnow().isoformat(),
                'job_queue': job_queue,
                'optimization_goals': optimization_goals,
                'jobs_analyzed': len(job_definitions),
                'recommendations': [],
                'summary': {},
                'implementation_plan': []
            }
            
            total_estimated_savings = 0.0
            total_time_savings = 0.0
            
            # Optimize each job definition
            for job_def in job_definitions:
                job_recommendations = self._optimize_single_job(job_def, goals, queue_config)
                optimization_result['recommendations'].extend(job_recommendations)
                
                for rec in job_recommendations:
                    total_estimated_savings += rec.estimated_cost_savings
                    total_time_savings += rec.estimated_time_savings
            
            # Optimize compute environment
            compute_env_recommendations = self._optimize_compute_environment(queue_config, goals)
            optimization_result['recommendations'].extend(compute_env_recommendations)
            
            # Generate implementation plan
            implementation_plan = self._generate_implementation_plan(optimization_result['recommendations'])
            optimization_result['implementation_plan'] = implementation_plan
            
            # Summary metrics
            optimization_result['summary'] = {
                'total_recommendations': len(optimization_result['recommendations']),
                'estimated_cost_savings_percent': total_estimated_savings,
                'estimated_time_savings_minutes': total_time_savings,
                'high_confidence_recommendations': len([r for r in optimization_result['recommendations'] 
                                                       if hasattr(r, 'confidence_score') and r.confidence_score > 0.8]),
                'implementation_complexity': self._assess_implementation_complexity(optimization_result['recommendations'])
            }
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Failed to optimize batch jobs: {e}")
            raise

    def _get_job_definitions(self, job_queue: str) -> List[Dict[str, Any]]:
        """Get job definitions associated with a queue"""
        try:
            # Get jobs from queue
            jobs_response = self.batch.list_jobs(
                jobQueue=job_queue,
                jobStatus='SUBMITTED'
            )
            
            job_definitions = []
            job_def_arns = set()
            
            # Collect unique job definition ARNs
            for job in jobs_response.get('jobList', []):
                job_def_arn = job.get('jobDefinitionArn')
                if job_def_arn:
                    job_def_arns.add(job_def_arn)
            
            # Get details for each job definition
            for job_def_arn in job_def_arns:
                try:
                    job_def_response = self.batch.describe_job_definitions(
                        jobDefinitions=[job_def_arn]
                    )
                    job_definitions.extend(job_def_response.get('jobDefinitions', []))
                except Exception as e:
                    logger.warning(f"Failed to get job definition {job_def_arn}: {e}")
            
            return job_definitions
            
        except Exception as e:
            logger.error(f"Failed to get job definitions for queue {job_queue}: {e}")
            return []

    def _get_queue_configuration(self, job_queue: str) -> Dict[str, Any]:
        """Get job queue configuration"""
        try:
            response = self.batch.describe_job_queues(jobQueues=[job_queue])
            if response['jobQueues']:
                return response['jobQueues'][0]
            return {}
        except Exception as e:
            logger.error(f"Failed to get queue configuration for {job_queue}: {e}")
            return {}

    def _optimize_single_job(self, job_definition: Dict[str, Any], goals: List[OptimizationGoal], 
                           queue_config: Dict[str, Any]) -> List[OptimizationRecommendation]:
        """Optimize a single job definition"""
        recommendations = []
        
        job_name = job_definition.get('jobDefinitionName', 'unknown')
        container_props = job_definition.get('containerProperties', {})
        
        current_config = {
            'vcpus': container_props.get('vcpus', 1),
            'memory': container_props.get('memory', 512),
            'job_role_arn': container_props.get('jobRoleArn'),
            'instance_types': []
        }
        
        # Infer job type from resource requirements
        job_type = self._infer_job_type(current_config)
        
        # Resource optimization
        if OptimizationGoal.COST in goals or OptimizationGoal.BALANCED in goals:
            resource_rec = self._optimize_resource_allocation(job_name, current_config, job_type)
            if resource_rec:
                recommendations.append(resource_rec)
        
        # Instance type optimization
        if OptimizationGoal.COST in goals or OptimizationGoal.TIME in goals:
            instance_rec = self._optimize_instance_selection(job_name, current_config, job_type, goals)
            if instance_rec:
                recommendations.append(instance_rec)
        
        # Spot instance optimization
        if OptimizationGoal.COST in goals:
            spot_rec = self._optimize_spot_usage(job_name, current_config, job_type)
            if spot_rec:
                recommendations.append(spot_rec)
        
        # Retry and timeout optimization
        if OptimizationGoal.RELIABILITY in goals or OptimizationGoal.BALANCED in goals:
            reliability_rec = self._optimize_reliability_settings(job_name, job_definition)
            if reliability_rec:
                recommendations.append(reliability_rec)
        
        return recommendations

    def _infer_job_type(self, config: Dict[str, Any]) -> JobType:
        """Infer job type from resource configuration"""
        vcpus = config.get('vcpus', 1)
        memory_mb = config.get('memory', 512)
        
        # Memory per vCPU ratio analysis
        memory_per_cpu = memory_mb / vcpus
        
        if memory_per_cpu > 8192:  # >8GB per vCPU
            return JobType.MEMORY_INTENSIVE
        elif memory_per_cpu < 2048:  # <2GB per vCPU
            return JobType.CPU_INTENSIVE
        elif vcpus >= 16:
            return JobType.CPU_INTENSIVE
        else:
            return JobType.MIXED_WORKLOAD

    def _optimize_resource_allocation(self, job_name: str, current_config: Dict[str, Any], 
                                    job_type: JobType) -> Optional[OptimizationRecommendation]:
        """Optimize vCPU and memory allocation"""
        vcpus = current_config.get('vcpus', 1)
        memory_mb = current_config.get('memory', 512)
        
        # Calculate optimal resource ratios based on job type
        optimal_ratios = {
            JobType.CPU_INTENSIVE: {'memory_per_cpu': 2048, 'cpu_multiplier': 1.2},
            JobType.MEMORY_INTENSIVE: {'memory_per_cpu': 8192, 'cpu_multiplier': 0.8},
            JobType.IO_INTENSIVE: {'memory_per_cpu': 4096, 'cpu_multiplier': 1.0},
            JobType.NETWORK_INTENSIVE: {'memory_per_cpu': 4096, 'cpu_multiplier': 1.1},
            JobType.MIXED_WORKLOAD: {'memory_per_cpu': 4096, 'cpu_multiplier': 1.0}
        }
        
        ratio = optimal_ratios.get(job_type, optimal_ratios[JobType.MIXED_WORKLOAD])
        current_ratio = memory_mb / vcpus
        
        # Check if current allocation is suboptimal
        if abs(current_ratio - ratio['memory_per_cpu']) / ratio['memory_per_cpu'] > 0.3:  # >30% difference
            optimal_memory = int(vcpus * ratio['memory_per_cpu'])
            optimal_vcpus = max(1, int(vcpus * ratio['cpu_multiplier']))
            
            # Calculate cost impact
            current_cost_factor = vcpus + (memory_mb / 1024 * 0.1)  # Simplified cost model
            new_cost_factor = optimal_vcpus + (optimal_memory / 1024 * 0.1)
            cost_savings = ((current_cost_factor - new_cost_factor) / current_cost_factor) * 100
            
            recommended_config = current_config.copy()
            recommended_config.update({
                'vcpus': optimal_vcpus,
                'memory': optimal_memory
            })
            
            return OptimizationRecommendation(
                job_name=job_name,
                current_config=current_config,
                recommended_config=recommended_config,
                optimization_type="resource_allocation",
                estimated_cost_savings=cost_savings,
                estimated_time_savings=max(0, (vcpus - optimal_vcpus) * 2),  # Rough estimate
                confidence_score=0.8,
                implementation_notes=f"Optimized for {job_type.value} workload pattern"
            )
        
        return None

    def _optimize_instance_selection(self, job_name: str, current_config: Dict[str, Any], 
                                   job_type: JobType, goals: List[OptimizationGoal]) -> Optional[OptimizationRecommendation]:
        """Optimize instance type selection"""
        vcpus = current_config.get('vcpus', 1)
        memory_mb = current_config.get('memory', 512)
        
        # Find suitable instance families for job type
        suitable_families = self.job_type_instances.get(job_type, ['m5'])
        
        # Find best instance type within suitable families
        best_instance = None
        best_score = float('inf')
        
        for instance_type, specs in self.compute_instances.items():
            instance_family = instance_type.split('.')[0]
            
            if instance_family not in suitable_families:
                continue
            
            # Check if instance can handle the resource requirements
            if specs['vcpus'] < vcpus or specs['memory'] < memory_mb:
                continue
            
            # Calculate efficiency score based on goals
            score = self._calculate_instance_efficiency_score(specs, goals, vcpus, memory_mb)
            
            if score < best_score:
                best_score = score
                best_instance = instance_type
        
        if best_instance:
            instance_specs = self.compute_instances[best_instance]
            current_cost = 1.0  # Baseline cost
            new_cost = instance_specs['cost_per_hour'] / self.compute_instances['m5.large']['cost_per_hour']
            cost_savings = ((current_cost - new_cost) / current_cost) * 100
            
            if abs(cost_savings) > 5:  # Only recommend if >5% difference
                recommended_config = current_config.copy()
                recommended_config['recommended_instance_types'] = [best_instance]
                
                return OptimizationRecommendation(
                    job_name=job_name,
                    current_config=current_config,
                    recommended_config=recommended_config,
                    optimization_type="instance_selection",
                    estimated_cost_savings=cost_savings,
                    estimated_time_savings=max(0, cost_savings * 0.5),  # Performance improvement estimate
                    confidence_score=0.75,
                    implementation_notes=f"Optimized instance selection for {job_type.value} workload"
                )
        
        return None

    def _calculate_instance_efficiency_score(self, instance_specs: Dict[str, Any], 
                                           goals: List[OptimizationGoal], vcpus: int, memory_mb: int) -> float:
        """Calculate efficiency score for instance type"""
        score = 0.0
        
        # Resource utilization score
        cpu_utilization = min(1.0, vcpus / instance_specs['vcpus'])
        memory_utilization = min(1.0, memory_mb / instance_specs['memory'])
        utilization_score = (cpu_utilization + memory_utilization) / 2
        
        # Cost efficiency score
        cost_score = 1.0 / (instance_specs['cost_per_hour'] + 0.001)  # Avoid division by zero
        
        # Weight scores based on goals
        if OptimizationGoal.COST in goals:
            score += cost_score * 0.6 + utilization_score * 0.4
        elif OptimizationGoal.TIME in goals:
            score += utilization_score * 0.7 + cost_score * 0.3
        else:  # Balanced
            score += utilization_score * 0.5 + cost_score * 0.5
        
        return 1.0 / score  # Lower is better

    def _optimize_spot_usage(self, job_name: str, current_config: Dict[str, Any], 
                           job_type: JobType) -> Optional[OptimizationRecommendation]:
        """Optimize spot instance usage"""
        # Check if job is suitable for spot instances
        # (fault-tolerant jobs are good candidates)
        
        spot_suitable_types = [JobType.CPU_INTENSIVE, JobType.MIXED_WORKLOAD, JobType.IO_INTENSIVE]
        
        if job_type in spot_suitable_types:
            # Estimate spot savings
            estimated_savings = 35  # Average 35% savings with spot
            
            recommended_config = current_config.copy()
            recommended_config['use_spot_instances'] = True
            recommended_config['spot_interruption_handling'] = 'retry'
            
            return OptimizationRecommendation(
                job_name=job_name,
                current_config=current_config,
                recommended_config=recommended_config,
                optimization_type="spot_optimization",
                estimated_cost_savings=estimated_savings,
                estimated_time_savings=0,
                confidence_score=0.7,
                implementation_notes="Enable spot instances with interruption handling"
            )
        
        return None

    def _optimize_reliability_settings(self, job_name: str, job_definition: Dict[str, Any]) -> Optional[OptimizationRecommendation]:
        """Optimize retry and timeout settings"""
        retry_strategy = job_definition.get('retryStrategy', {})
        timeout = job_definition.get('timeout', {})
        
        current_attempts = retry_strategy.get('attempts', 1)
        current_timeout = timeout.get('attemptDurationSeconds', 0)
        
        # Recommend optimal retry strategy
        recommended_attempts = 3  # Standard for most batch jobs
        recommended_timeout = max(3600, current_timeout or 3600)  # At least 1 hour
        
        if current_attempts != recommended_attempts or abs(current_timeout - recommended_timeout) > 1800:
            recommended_config = {
                'retry_attempts': recommended_attempts,
                'timeout_seconds': recommended_timeout,
                'failure_handling': 'exponential_backoff'
            }
            
            current_config = {
                'retry_attempts': current_attempts,
                'timeout_seconds': current_timeout
            }
            
            return OptimizationRecommendation(
                job_name=job_name,
                current_config=current_config,
                recommended_config=recommended_config,
                optimization_type="reliability_optimization",
                estimated_cost_savings=0,
                estimated_time_savings=0,
                confidence_score=0.9,
                implementation_notes="Improved reliability with optimal retry and timeout settings"
            )
        
        return None

    def _optimize_compute_environment(self, queue_config: Dict[str, Any], 
                                    goals: List[OptimizationGoal]) -> List[OptimizationRecommendation]:
        """Optimize compute environment configuration"""
        recommendations = []
        
        # Get compute environment details
        compute_env_order = queue_config.get('computeEnvironmentOrder', [])
        
        for env_config in compute_env_order:
            env_name = env_config.get('computeEnvironment')
            
            if env_name:
                try:
                    env_response = self.batch.describe_compute_environments(
                        computeEnvironments=[env_name]
                    )
                    
                    if env_response['computeEnvironments']:
                        env_details = env_response['computeEnvironments'][0]
                        env_recommendations = self._analyze_compute_environment(env_details, goals)
                        recommendations.extend(env_recommendations)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze compute environment {env_name}: {e}")
        
        return recommendations

    def _analyze_compute_environment(self, env_details: Dict[str, Any], 
                                   goals: List[OptimizationGoal]) -> List[OptimizationRecommendation]:
        """Analyze and optimize compute environment configuration"""
        recommendations = []
        
        compute_resources = env_details.get('computeResources', {})
        env_name = env_details.get('computeEnvironmentName', 'unknown')
        
        current_config = {
            'instance_types': compute_resources.get('instanceTypes', []),
            'min_vcpus': compute_resources.get('minvCpus', 0),
            'max_vcpus': compute_resources.get('maxvCpus', 256),
            'desired_vcpus': compute_resources.get('desiredvCpus', 0),
            'spot_iam_fleet_request_role': compute_resources.get('spotIamFleetRequestRole')
        }
        
        # Instance type optimization
        if 'optimal' not in current_config['instance_types']:
            recommended_config = current_config.copy()
            recommended_config['instance_types'] = ['optimal']
            
            recommendations.append(OptimizationRecommendation(
                job_name=f"compute_env_{env_name}",
                current_config=current_config,
                recommended_config=recommended_config,
                optimization_type="compute_environment_instances",
                estimated_cost_savings=15,
                estimated_time_savings=0,
                confidence_score=0.8,
                implementation_notes="Use 'optimal' instance selection for better cost efficiency"
            ))
        
        # Spot instance configuration
        if OptimizationGoal.COST in goals and not current_config.get('spot_iam_fleet_request_role'):
            recommended_config = current_config.copy()
            recommended_config['enable_spot_fleet'] = True
            recommended_config['spot_allocation_strategy'] = 'spot_capacity_optimized'
            
            recommendations.append(OptimizationRecommendation(
                job_name=f"compute_env_{env_name}",
                current_config=current_config,
                recommended_config=recommended_config,
                optimization_type="compute_environment_spot",
                estimated_cost_savings=40,
                estimated_time_savings=0,
                confidence_score=0.7,
                implementation_notes="Enable spot instances in compute environment for cost savings"
            ))
        
        return recommendations

    def _generate_implementation_plan(self, recommendations: List[OptimizationRecommendation]) -> List[Dict[str, Any]]:
        """Generate implementation plan for recommendations"""
        plan = []
        
        # Group by optimization type and priority
        priority_order = [
            "spot_optimization",
            "compute_environment_spot",
            "instance_selection",
            "compute_environment_instances",
            "resource_allocation",
            "reliability_optimization"
        ]
        
        grouped_recommendations = {}
        for rec in recommendations:
            opt_type = rec.optimization_type
            if opt_type not in grouped_recommendations:
                grouped_recommendations[opt_type] = []
            grouped_recommendations[opt_type].append(rec)
        
        # Create implementation steps
        for opt_type in priority_order:
            if opt_type in grouped_recommendations:
                recs = grouped_recommendations[opt_type]
                
                plan.append({
                    'step': len(plan) + 1,
                    'optimization_type': opt_type,
                    'job_count': len(recs),
                    'estimated_effort': self._estimate_implementation_effort(opt_type, recs),
                    'prerequisites': self._get_prerequisites(opt_type),
                    'rollback_plan': self._get_rollback_plan(opt_type),
                    'validation_steps': self._get_validation_steps(opt_type),
                    'jobs_affected': [rec.job_name for rec in recs]
                })
        
        return plan

    def _estimate_implementation_effort(self, opt_type: str, recommendations: List[OptimizationRecommendation]) -> str:
        """Estimate implementation effort"""
        effort_map = {
            "resource_allocation": "Low",
            "instance_selection": "Medium",
            "spot_optimization": "Medium",
            "reliability_optimization": "Low",
            "compute_environment_instances": "High",
            "compute_environment_spot": "High"
        }
        
        return effort_map.get(opt_type, "Medium")

    def _get_prerequisites(self, opt_type: str) -> List[str]:
        """Get prerequisites for optimization type"""
        prerequisites_map = {
            "spot_optimization": [
                "Ensure jobs are fault-tolerant",
                "Set up proper IAM roles for spot fleet",
                "Test spot interruption handling"
            ],
            "compute_environment_spot": [
                "Create spot fleet IAM role",
                "Configure spot allocation strategy",
                "Set up interruption monitoring"
            ],
            "instance_selection": [
                "Validate new instance types in test environment",
                "Check application compatibility"
            ],
            "resource_allocation": [
                "Profile actual resource usage",
                "Test with new resource limits"
            ]
        }
        
        return prerequisites_map.get(opt_type, [])

    def _get_rollback_plan(self, opt_type: str) -> str:
        """Get rollback plan for optimization type"""
        return f"Revert {opt_type} changes by updating job definitions to previous configuration"

    def _get_validation_steps(self, opt_type: str) -> List[str]:
        """Get validation steps for optimization type"""
        return [
            "Monitor job completion rates",
            "Check cost metrics",
            "Validate performance benchmarks",
            "Review error rates and retries"
        ]

    def _assess_implementation_complexity(self, recommendations: List[OptimizationRecommendation]) -> str:
        """Assess overall implementation complexity"""
        if len(recommendations) > 10:
            return "High"
        elif len(recommendations) > 5:
            return "Medium"
        else:
            return "Low"

    def get_batch_metrics(self, job_queue: str) -> Dict[str, Any]:
        """Get batch job queue metrics"""
        try:
            metrics = {
                'timestamp': datetime.utcnow().isoformat(),
                'job_queue': job_queue,
                'queue_metrics': {},
                'cost_analysis': {},
                'performance_analysis': {}
            }
            
            # Get queue status
            queue_response = self.batch.describe_job_queues(jobQueues=[job_queue])
            if not queue_response['jobQueues']:
                return {'error': f'Job queue {job_queue} not found'}
            
            queue_info = queue_response['jobQueues'][0]
            
            # Get job counts by status
            job_counts = {}
            for status in ['SUBMITTED', 'PENDING', 'RUNNABLE', 'STARTING', 'RUNNING', 'SUCCEEDED', 'FAILED']:
                jobs = self.batch.list_jobs(jobQueue=job_queue, jobStatus=status)
                job_counts[status.lower()] = len(jobs.get('jobList', []))
            
            metrics['queue_metrics'] = {
                'queue_state': queue_info.get('state'),
                'priority': queue_info.get('priority', 0),
                'job_counts': job_counts,
                'total_jobs': sum(job_counts.values())
            }
            
            # Analyze recent job performance
            recent_jobs = self.batch.list_jobs(
                jobQueue=job_queue,
                jobStatus='SUCCEEDED',
                maxResults=50
            )
            
            if recent_jobs.get('jobList'):
                runtimes = []
                for job in recent_jobs['jobList']:
                    if job.get('startedAt') and job.get('stoppedAt'):
                        runtime = job['stoppedAt'] - job['startedAt']
                        runtimes.append(runtime / 1000 / 60)  # Convert to minutes
                
                if runtimes:
                    metrics['performance_analysis'] = {
                        'avg_runtime_minutes': sum(runtimes) / len(runtimes),
                        'max_runtime_minutes': max(runtimes),
                        'min_runtime_minutes': min(runtimes),
                        'jobs_analyzed': len(runtimes)
                    }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get batch metrics: {e}")
            return {'error': str(e)}

    def estimate_job_cost(self, job_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate cost for running a batch job"""
        try:
            vcpus = job_spec.get('vcpus', 1)
            memory_mb = job_spec.get('memory', 512)
            runtime_minutes = job_spec.get('estimated_runtime_minutes', 60)
            
            # Find best instance type for job
            best_instance = self._find_best_instance_for_job(vcpus, memory_mb)
            
            if not best_instance:
                return {'error': 'No suitable instance type found'}
            
            instance_specs = self.compute_instances[best_instance]
            
            # Calculate costs
            runtime_hours = runtime_minutes / 60.0
            on_demand_cost = instance_specs['cost_per_hour'] * runtime_hours
            
            # Estimate spot cost
            instance_family = best_instance.split('.')[0]
            spot_discount = self.spot_discounts.get(instance_family, 0.7)
            spot_cost = on_demand_cost * spot_discount
            
            return {
                'recommended_instance': best_instance,
                'estimated_runtime_hours': runtime_hours,
                'costs': {
                    'on_demand': round(on_demand_cost, 4),
                    'spot': round(spot_cost, 4),
                    'savings_with_spot_percent': round((1 - spot_discount) * 100, 1)
                },
                'resource_utilization': {
                    'vcpu_utilization_percent': min(100, (vcpus / instance_specs['vcpus']) * 100),
                    'memory_utilization_percent': min(100, (memory_mb / instance_specs['memory']) * 100)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to estimate job cost: {e}")
            return {'error': str(e)}

    def _find_best_instance_for_job(self, vcpus: int, memory_mb: int) -> Optional[str]:
        """Find the most cost-effective instance type for job requirements"""
        suitable_instances = []
        
        for instance_type, specs in self.compute_instances.items():
            if specs['vcpus'] >= vcpus and specs['memory'] >= memory_mb:
                # Calculate efficiency (resource utilization / cost)
                cpu_util = vcpus / specs['vcpus']
                mem_util = memory_mb / specs['memory']
                avg_util = (cpu_util + mem_util) / 2
                efficiency = avg_util / specs['cost_per_hour']
                
                suitable_instances.append((efficiency, instance_type))
        
        if suitable_instances:
            # Sort by efficiency (higher is better)
            suitable_instances.sort(reverse=True)
            return suitable_instances[0][1]
        
        return None