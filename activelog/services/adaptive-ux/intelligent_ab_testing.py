#!/usr/bin/env python3
"""
Intelligent A/B Testing Framework for Adaptive UX System

This module provides advanced A/B testing capabilities with AI-driven experiment design,
real-time adaptation, statistical significance monitoring, and automated optimization
for the adaptive UX system.
"""

import asyncio
import json
import logging
import numpy as np
import scipy.stats as stats
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import networkx as nx

class ExperimentType(Enum):
    """Types of A/B test experiments"""
    INTERFACE_LAYOUT = "interface_layout"
    FEATURE_PLACEMENT = "feature_placement"
    COLOR_SCHEME = "color_scheme"
    NAVIGATION_STYLE = "navigation_style"
    CONTENT_DENSITY = "content_density"
    INTERACTION_PATTERN = "interaction_pattern"
    ONBOARDING_FLOW = "onboarding_flow"
    PERSONALIZATION_STRATEGY = "personalization_strategy"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ACCESSIBILITY_ENHANCEMENT = "accessibility_enhancement"

class ExperimentStatus(Enum):
    """Status of A/B test experiments"""
    DRAFT = "draft"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"
    ANALYZING = "analyzing"

class StatisticalTest(Enum):
    """Statistical tests for experiment analysis"""
    T_TEST = "t_test"
    CHI_SQUARE = "chi_square"
    MANN_WHITNEY = "mann_whitney"
    ANOVA = "anova"
    BAYESIAN = "bayesian"
    BOOTSTRAP = "bootstrap"

class TrafficAllocation(Enum):
    """Traffic allocation strategies"""
    RANDOM = "random"
    STRATIFIED = "stratified"
    ADAPTIVE = "adaptive"
    CONTEXTUAL = "contextual"
    BANDIT = "bandit"
    BAYESIAN_OPTIMIZATION = "bayesian_optimization"

@dataclass
class ExperimentVariant:
    """A variant in an A/B test experiment"""
    variant_id: str
    name: str
    description: str
    configuration: Dict[str, Any]
    traffic_allocation: float = 0.5  # 0.0 to 1.0
    is_control: bool = False
    active: bool = True
    
@dataclass
class ExperimentMetric:
    """Metric to track in an experiment"""
    metric_id: str
    name: str
    description: str
    metric_type: str  # 'primary', 'secondary', 'guardrail'
    data_type: str   # 'continuous', 'binary', 'count', 'rate'
    goal: str        # 'increase', 'decrease', 'no_change'
    statistical_test: StatisticalTest = StatisticalTest.T_TEST
    minimum_effect_size: float = 0.05
    significance_level: float = 0.05
    power: float = 0.8

@dataclass
class ExperimentResult:
    """Results of an experiment metric"""
    metric_id: str
    variant_id: str
    sample_size: int
    mean: float
    std_dev: float
    confidence_interval: Tuple[float, float]
    p_value: Optional[float] = None
    effect_size: Optional[float] = None
    statistical_significance: bool = False
    practical_significance: bool = False

@dataclass
class ExperimentConfiguration:
    """Configuration for an A/B test experiment"""
    experiment_id: str
    name: str
    description: str
    experiment_type: ExperimentType
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Experiment parameters
    variants: List[ExperimentVariant] = field(default_factory=list)
    metrics: List[ExperimentMetric] = field(default_factory=list)
    target_audience: Dict[str, Any] = field(default_factory=dict)
    exclusion_criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Traffic and timing
    traffic_allocation_strategy: TrafficAllocation = TrafficAllocation.RANDOM
    min_sample_size: int = 1000
    max_duration_days: int = 30
    min_duration_days: int = 7
    
    # Statistical parameters
    significance_level: float = 0.05
    power: float = 0.8
    minimum_detectable_effect: float = 0.05
    
    # Experiment metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Results
    results: List[ExperimentResult] = field(default_factory=list)
    winner: Optional[str] = None
    conclusion: str = ""

@dataclass
class UserAssignment:
    """User assignment to experiment variant"""
    user_id: str
    experiment_id: str
    variant_id: str
    assigned_at: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ExperimentEvent:
    """Event recorded during an experiment"""
    event_id: str
    user_id: str
    experiment_id: str
    variant_id: str
    metric_id: str
    value: Union[float, int, bool]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = field(default_factory=dict)

class ExperimentDesigner:
    """AI-powered experiment design and optimization"""
    
    def __init__(self):
        self.design_templates = self._initialize_design_templates()
        self.statistical_models = self._initialize_statistical_models()
        self.logger = logging.getLogger(__name__)
    
    def _initialize_design_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize experiment design templates"""
        return {
            'interface_layout': {
                'suggested_metrics': [
                    {'name': 'task_completion_rate', 'type': 'primary', 'data_type': 'binary'},
                    {'name': 'time_to_completion', 'type': 'primary', 'data_type': 'continuous'},
                    {'name': 'user_satisfaction', 'type': 'secondary', 'data_type': 'continuous'},
                    {'name': 'error_rate', 'type': 'guardrail', 'data_type': 'rate'}
                ],
                'min_sample_size': 2000,
                'recommended_duration': 14,
                'traffic_split': {'control': 0.5, 'variant': 0.5}
            },
            'feature_placement': {
                'suggested_metrics': [
                    {'name': 'feature_discovery_rate', 'type': 'primary', 'data_type': 'binary'},
                    {'name': 'feature_usage_rate', 'type': 'primary', 'data_type': 'rate'},
                    {'name': 'click_through_rate', 'type': 'secondary', 'data_type': 'rate'},
                    {'name': 'user_confusion_score', 'type': 'guardrail', 'data_type': 'continuous'}
                ],
                'min_sample_size': 1500,
                'recommended_duration': 10,
                'traffic_split': {'control': 0.4, 'variant': 0.6}
            },
            'onboarding_flow': {
                'suggested_metrics': [
                    {'name': 'onboarding_completion_rate', 'type': 'primary', 'data_type': 'binary'},
                    {'name': 'time_to_first_value', 'type': 'primary', 'data_type': 'continuous'},
                    {'name': 'activation_rate', 'type': 'secondary', 'data_type': 'binary'},
                    {'name': 'retention_rate_7d', 'type': 'secondary', 'data_type': 'binary'}
                ],
                'min_sample_size': 3000,
                'recommended_duration': 21,
                'traffic_split': {'control': 0.5, 'variant': 0.5}
            },
            'personalization_strategy': {
                'suggested_metrics': [
                    {'name': 'engagement_score', 'type': 'primary', 'data_type': 'continuous'},
                    {'name': 'feature_adoption_rate', 'type': 'primary', 'data_type': 'rate'},
                    {'name': 'user_satisfaction', 'type': 'secondary', 'data_type': 'continuous'},
                    {'name': 'churn_rate', 'type': 'guardrail', 'data_type': 'rate'}
                ],
                'min_sample_size': 5000,
                'recommended_duration': 28,
                'traffic_split': {'control': 0.3, 'variant_a': 0.35, 'variant_b': 0.35}
            }
        }
    
    def _initialize_statistical_models(self) -> Dict[str, Any]:
        """Initialize statistical models for experiment analysis"""
        return {
            'power_analysis': {
                'continuous_metrics': self._calculate_continuous_power,
                'binary_metrics': self._calculate_binary_power,
                'rate_metrics': self._calculate_rate_power
            },
            'sample_size_calculation': {
                'continuous_metrics': self._calculate_continuous_sample_size,
                'binary_metrics': self._calculate_binary_sample_size,
                'rate_metrics': self._calculate_rate_sample_size
            },
            'effect_size_estimation': {
                'cohen_d': self._calculate_cohens_d,
                'odds_ratio': self._calculate_odds_ratio,
                'relative_risk': self._calculate_relative_risk
            }
        }
    
    def design_experiment(self, experiment_type: ExperimentType, 
                         objectives: List[str],
                         constraints: Dict[str, Any] = None) -> ExperimentConfiguration:
        """Design an experiment based on type and objectives"""
        constraints = constraints or {}
        
        # Get design template
        template = self.design_templates.get(experiment_type.value, {})
        
        # Generate experiment configuration
        experiment_id = self._generate_experiment_id(experiment_type)
        
        config = ExperimentConfiguration(
            experiment_id=experiment_id,
            name=f"{experiment_type.value.replace('_', ' ').title()} Test",
            description=f"Testing {', '.join(objectives)}",
            experiment_type=experiment_type
        )
        
        # Add suggested metrics
        if 'suggested_metrics' in template:
            for metric_template in template['suggested_metrics']:
                metric = ExperimentMetric(
                    metric_id=f"{experiment_id}_{metric_template['name']}",
                    name=metric_template['name'],
                    description=f"Measures {metric_template['name'].replace('_', ' ')}",
                    metric_type=metric_template['type'],
                    data_type=metric_template['data_type'],
                    goal='increase' if 'rate' in metric_template['name'] or 'completion' in metric_template['name'] else 'improve'
                )
                config.metrics.append(metric)
        
        # Set sample size and duration
        config.min_sample_size = template.get('min_sample_size', 1000)
        config.max_duration_days = template.get('recommended_duration', 14)
        
        # Apply constraints
        if 'max_sample_size' in constraints:
            config.min_sample_size = min(config.min_sample_size, constraints['max_sample_size'])
        
        if 'max_duration' in constraints:
            config.max_duration_days = min(config.max_duration_days, constraints['max_duration'])
        
        # Generate variants based on objectives
        variants = self._generate_variants(experiment_type, objectives, template)
        config.variants = variants
        
        self.logger.info(f"Designed experiment {experiment_id} with {len(variants)} variants and {len(config.metrics)} metrics")
        
        return config
    
    def _generate_experiment_id(self, experiment_type: ExperimentType) -> str:
        """Generate unique experiment ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        type_code = experiment_type.value[:4].upper()
        return f"EXP_{type_code}_{timestamp}"
    
    def _generate_variants(self, experiment_type: ExperimentType, 
                          objectives: List[str], 
                          template: Dict[str, Any]) -> List[ExperimentVariant]:
        """Generate experiment variants based on objectives"""
        variants = []
        
        # Control variant
        control = ExperimentVariant(
            variant_id=f"control_{experiment_type.value}",
            name="Control",
            description="Current implementation (control group)",
            configuration={'variant_type': 'control'},
            is_control=True
        )
        variants.append(control)
        
        # Generate test variants based on experiment type
        if experiment_type == ExperimentType.INTERFACE_LAYOUT:
            variants.extend(self._generate_layout_variants(objectives))
        elif experiment_type == ExperimentType.FEATURE_PLACEMENT:
            variants.extend(self._generate_placement_variants(objectives))
        elif experiment_type == ExperimentType.ONBOARDING_FLOW:
            variants.extend(self._generate_onboarding_variants(objectives))
        elif experiment_type == ExperimentType.PERSONALIZATION_STRATEGY:
            variants.extend(self._generate_personalization_variants(objectives))
        else:
            # Generic variant generation
            for i, objective in enumerate(objectives[:3]):  # Max 3 variants + control
                variant = ExperimentVariant(
                    variant_id=f"variant_{chr(65+i)}_{experiment_type.value}",
                    name=f"Variant {chr(65+i)}",
                    description=f"Testing {objective}",
                    configuration={'objective': objective, 'variant_type': 'test'}
                )
                variants.append(variant)
        
        # Set traffic allocation
        if len(variants) > 1:
            allocation_per_variant = 1.0 / len(variants)
            for variant in variants:
                variant.traffic_allocation = allocation_per_variant
        
        return variants
    
    def _generate_layout_variants(self, objectives: List[str]) -> List[ExperimentVariant]:
        """Generate layout-specific variants"""
        variants = []
        
        layout_options = {
            'compact_layout': {
                'layout_density': 'high',
                'spacing': 'minimal',
                'information_density': 'high'
            },
            'spacious_layout': {
                'layout_density': 'low',
                'spacing': 'generous',
                'information_density': 'low'
            },
            'adaptive_layout': {
                'layout_density': 'adaptive',
                'spacing': 'context_aware',
                'information_density': 'user_preference'
            }
        }
        
        for i, (layout_name, config) in enumerate(layout_options.items()):
            if i >= len(objectives):
                break
                
            variant = ExperimentVariant(
                variant_id=f"layout_{layout_name}",
                name=layout_name.replace('_', ' ').title(),
                description=f"Layout optimized for {objectives[i] if i < len(objectives) else 'general use'}",
                configuration=config
            )
            variants.append(variant)
        
        return variants
    
    def _generate_placement_variants(self, objectives: List[str]) -> List[ExperimentVariant]:
        """Generate feature placement variants"""
        variants = []
        
        placement_strategies = {
            'top_navigation': {
                'primary_navigation': 'top',
                'feature_placement': 'header',
                'accessibility': 'high'
            },
            'sidebar_navigation': {
                'primary_navigation': 'sidebar',
                'feature_placement': 'side_panel',
                'accessibility': 'medium'
            },
            'contextual_placement': {
                'primary_navigation': 'contextual',
                'feature_placement': 'adaptive',
                'accessibility': 'dynamic'
            }
        }
        
        for i, (placement_name, config) in enumerate(placement_strategies.items()):
            if i >= len(objectives):
                break
                
            variant = ExperimentVariant(
                variant_id=f"placement_{placement_name}",
                name=placement_name.replace('_', ' ').title(),
                description=f"Feature placement for {objectives[i] if i < len(objectives) else 'discoverability'}",
                configuration=config
            )
            variants.append(variant)
        
        return variants
    
    def _generate_onboarding_variants(self, objectives: List[str]) -> List[ExperimentVariant]:
        """Generate onboarding flow variants"""
        variants = []
        
        onboarding_flows = {
            'progressive_onboarding': {
                'flow_type': 'progressive',
                'steps': 'minimal_initial',
                'feature_introduction': 'gradual',
                'user_control': 'high'
            },
            'comprehensive_onboarding': {
                'flow_type': 'comprehensive',
                'steps': 'complete_upfront',
                'feature_introduction': 'immediate',
                'user_control': 'guided'
            },
            'contextual_onboarding': {
                'flow_type': 'contextual',
                'steps': 'just_in_time',
                'feature_introduction': 'contextual',
                'user_control': 'adaptive'
            }
        }
        
        for i, (flow_name, config) in enumerate(onboarding_flows.items()):
            if i >= len(objectives):
                break
                
            variant = ExperimentVariant(
                variant_id=f"onboarding_{flow_name}",
                name=flow_name.replace('_', ' ').title(),
                description=f"Onboarding optimized for {objectives[i] if i < len(objectives) else 'user success'}",
                configuration=config
            )
            variants.append(variant)
        
        return variants
    
    def _generate_personalization_variants(self, objectives: List[str]) -> List[ExperimentVariant]:
        """Generate personalization strategy variants"""
        variants = []
        
        personalization_strategies = {
            'behavioral_personalization': {
                'strategy': 'behavioral',
                'adaptation_speed': 'fast',
                'personalization_depth': 'interface',
                'data_source': 'implicit'
            },
            'explicit_personalization': {
                'strategy': 'explicit',
                'adaptation_speed': 'immediate',
                'personalization_depth': 'preferences',
                'data_source': 'explicit'
            },
            'hybrid_personalization': {
                'strategy': 'hybrid',
                'adaptation_speed': 'moderate',
                'personalization_depth': 'comprehensive',
                'data_source': 'combined'
            }
        }
        
        for i, (strategy_name, config) in enumerate(personalization_strategies.items()):
            if i >= len(objectives):
                break
                
            variant = ExperimentVariant(
                variant_id=f"personalization_{strategy_name}",
                name=strategy_name.replace('_', ' ').title(),
                description=f"Personalization for {objectives[i] if i < len(objectives) else 'user engagement'}",
                configuration=config
            )
            variants.append(variant)
        
        return variants
    
    # Statistical power and sample size calculations
    def _calculate_continuous_power(self, effect_size: float, sample_size: int, alpha: float = 0.05) -> float:
        """Calculate statistical power for continuous metrics"""
        from scipy.stats import norm
        
        # Cohen's d to power calculation
        critical_z = norm.ppf(1 - alpha/2)
        power_z = norm.ppf(1 - 0.2)  # 80% power
        
        # Effect size adjusted for sample size
        adjusted_effect = effect_size * np.sqrt(sample_size / 2)
        
        power = 1 - norm.cdf(critical_z - adjusted_effect)
        return min(power, 0.99)
    
    def _calculate_binary_power(self, p1: float, p2: float, sample_size: int, alpha: float = 0.05) -> float:
        """Calculate statistical power for binary metrics"""
        from scipy.stats import norm
        
        # Pooled proportion
        p_pool = (p1 + p2) / 2
        
        # Standard error
        se = np.sqrt(2 * p_pool * (1 - p_pool) / sample_size)
        
        # Effect size
        effect = abs(p2 - p1)
        
        # Power calculation
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = (effect - z_alpha * se) / se
        
        power = norm.cdf(z_beta)
        return min(max(power, 0.05), 0.99)
    
    def _calculate_rate_power(self, rate1: float, rate2: float, sample_size: int, alpha: float = 0.05) -> float:
        """Calculate statistical power for rate metrics"""
        # Similar to binary but accounting for rate nature
        return self._calculate_binary_power(rate1, rate2, sample_size, alpha)
    
    def _calculate_continuous_sample_size(self, effect_size: float, power: float = 0.8, alpha: float = 0.05) -> int:
        """Calculate sample size for continuous metrics"""
        from scipy.stats import norm
        
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        
        # Sample size per group
        n = 2 * ((z_alpha + z_beta) / effect_size) ** 2
        
        return max(int(np.ceil(n)), 100)  # Minimum 100 per group
    
    def _calculate_binary_sample_size(self, p1: float, p2: float, power: float = 0.8, alpha: float = 0.05) -> int:
        """Calculate sample size for binary metrics"""
        from scipy.stats import norm
        
        z_alpha = norm.ppf(1 - alpha/2)
        z_beta = norm.ppf(power)
        
        # Pooled proportion
        p_pool = (p1 + p2) / 2
        
        # Sample size calculation
        numerator = (z_alpha * np.sqrt(2 * p_pool * (1 - p_pool)) + z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        denominator = (p2 - p1) ** 2
        
        n = numerator / denominator
        
        return max(int(np.ceil(n)), 100)
    
    def _calculate_rate_sample_size(self, rate1: float, rate2: float, power: float = 0.8, alpha: float = 0.05) -> int:
        """Calculate sample size for rate metrics"""
        # Convert rates to proportions and use binary calculation
        p1 = min(rate1, 0.99)  # Cap at 99%
        p2 = min(rate2, 0.99)
        return self._calculate_binary_sample_size(p1, p2, power, alpha)
    
    def _calculate_cohens_d(self, mean1: float, mean2: float, std1: float, std2: float) -> float:
        """Calculate Cohen's d effect size"""
        pooled_std = np.sqrt((std1**2 + std2**2) / 2)
        return abs(mean2 - mean1) / pooled_std if pooled_std > 0 else 0
    
    def _calculate_odds_ratio(self, success1: int, total1: int, success2: int, total2: int) -> float:
        """Calculate odds ratio"""
        odds1 = success1 / (total1 - success1) if total1 > success1 else float('inf')
        odds2 = success2 / (total2 - success2) if total2 > success2 else float('inf')
        
        return odds2 / odds1 if odds1 > 0 and odds1 != float('inf') else float('inf')
    
    def _calculate_relative_risk(self, success1: int, total1: int, success2: int, total2: int) -> float:
        """Calculate relative risk"""
        rate1 = success1 / total1 if total1 > 0 else 0
        rate2 = success2 / total2 if total2 > 0 else 0
        
        return rate2 / rate1 if rate1 > 0 else float('inf')

class TrafficAllocator:
    """Intelligent traffic allocation for A/B tests"""
    
    def __init__(self):
        self.allocation_strategies = {
            TrafficAllocation.RANDOM: self._random_allocation,
            TrafficAllocation.STRATIFIED: self._stratified_allocation,
            TrafficAllocation.ADAPTIVE: self._adaptive_allocation,
            TrafficAllocation.CONTEXTUAL: self._contextual_allocation,
            TrafficAllocation.BANDIT: self._bandit_allocation,
            TrafficAllocation.BAYESIAN_OPTIMIZATION: self._bayesian_allocation
        }
        self.bandit_models: Dict[str, Any] = {}
        self.allocation_history: Dict[str, List[UserAssignment]] = defaultdict(list)
        self.logger = logging.getLogger(__name__)
    
    def allocate_user(self, user_id: str, experiment: ExperimentConfiguration,
                     user_context: Dict[str, Any] = None) -> str:
        """Allocate user to experiment variant"""
        strategy = experiment.traffic_allocation_strategy
        allocation_func = self.allocation_strategies.get(strategy, self._random_allocation)
        
        variant_id = allocation_func(user_id, experiment, user_context or {})
        
        # Record assignment
        assignment = UserAssignment(
            user_id=user_id,
            experiment_id=experiment.experiment_id,
            variant_id=variant_id,
            context=user_context or {}
        )
        
        self.allocation_history[experiment.experiment_id].append(assignment)
        
        self.logger.debug(f"Allocated user {user_id} to variant {variant_id} in experiment {experiment.experiment_id}")
        
        return variant_id
    
    def _random_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                          context: Dict[str, Any]) -> str:
        """Random traffic allocation"""
        # Use user ID for consistent assignment
        import hashlib
        hash_input = f"{user_id}_{experiment.experiment_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        random_value = (hash_value % 10000) / 10000.0
        
        cumulative_allocation = 0.0
        for variant in experiment.variants:
            if not variant.active:
                continue
                
            cumulative_allocation += variant.traffic_allocation
            if random_value <= cumulative_allocation:
                return variant.variant_id
        
        # Fallback to control
        control_variants = [v for v in experiment.variants if v.is_control]
        return control_variants[0].variant_id if control_variants else experiment.variants[0].variant_id
    
    def _stratified_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                              context: Dict[str, Any]) -> str:
        """Stratified allocation based on user characteristics"""
        # Create strata based on user context
        strata_key = self._create_strata_key(context)
        
        # Use strata-specific random allocation
        import hashlib
        hash_input = f"{user_id}_{experiment.experiment_id}_{strata_key}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        random_value = (hash_value % 10000) / 10000.0
        
        # Allocate within strata
        cumulative_allocation = 0.0
        for variant in experiment.variants:
            if not variant.active:
                continue
                
            cumulative_allocation += variant.traffic_allocation
            if random_value <= cumulative_allocation:
                return variant.variant_id
        
        return self._random_allocation(user_id, experiment, context)
    
    def _create_strata_key(self, context: Dict[str, Any]) -> str:
        """Create stratification key from user context"""
        strata_factors = []
        
        # Device type
        device_type = context.get('device_type', 'unknown')
        strata_factors.append(f"device:{device_type}")
        
        # User segment
        user_segment = context.get('user_segment', 'unknown')
        strata_factors.append(f"segment:{user_segment}")
        
        # Geographic region
        region = context.get('region', 'unknown')
        strata_factors.append(f"region:{region}")
        
        return "|".join(strata_factors)
    
    def _adaptive_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                           context: Dict[str, Any]) -> str:
        """Adaptive allocation based on experiment performance"""
        experiment_id = experiment.experiment_id
        
        # If experiment is new, use random allocation
        if experiment_id not in self.allocation_history or len(self.allocation_history[experiment_id]) < 100:
            return self._random_allocation(user_id, experiment, context)
        
        # Calculate performance metrics for each variant
        variant_performance = self._calculate_variant_performance(experiment_id)
        
        if not variant_performance:
            return self._random_allocation(user_id, experiment, context)
        
        # Adjust allocations based on performance
        total_performance = sum(variant_performance.values())
        
        if total_performance <= 0:
            return self._random_allocation(user_id, experiment, context)
        
        # Create performance-weighted allocation
        import hashlib
        hash_input = f"{user_id}_{experiment_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
        random_value = (hash_value % 10000) / 10000.0
        
        cumulative_weight = 0.0
        for variant in experiment.variants:
            if not variant.active:
                continue
                
            performance_weight = variant_performance.get(variant.variant_id, 1.0) / total_performance
            cumulative_weight += performance_weight
            
            if random_value <= cumulative_weight:
                return variant.variant_id
        
        return self._random_allocation(user_id, experiment, context)
    
    def _calculate_variant_performance(self, experiment_id: str) -> Dict[str, float]:
        """Calculate performance scores for variants"""
        # This is a simplified implementation
        # In practice, would analyze actual experiment results
        
        assignments = self.allocation_history.get(experiment_id, [])
        if not assignments:
            return {}
        
        # Count assignments per variant
        variant_counts = defaultdict(int)
        for assignment in assignments:
            variant_counts[assignment.variant_id] += 1
        
        # Simple performance metric (inverse of assignment count for exploration)
        performance = {}
        total_assignments = sum(variant_counts.values())
        
        for variant_id, count in variant_counts.items():
            # Encourage exploration of less-tested variants
            performance[variant_id] = 1.0 - (count / total_assignments) + 0.1
        
        return performance
    
    def _contextual_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                             context: Dict[str, Any]) -> str:
        """Context-aware allocation"""
        # Analyze context to determine optimal variant
        context_score = self._calculate_context_score(context, experiment)
        
        # Find best matching variant based on context
        best_variant = None
        best_score = -1
        
        for variant in experiment.variants:
            if not variant.active:
                continue
                
            variant_context_fit = self._calculate_variant_context_fit(variant, context)
            
            if variant_context_fit > best_score:
                best_score = variant_context_fit
                best_variant = variant
        
        return best_variant.variant_id if best_variant else self._random_allocation(user_id, experiment, context)
    
    def _calculate_context_score(self, context: Dict[str, Any], experiment: ExperimentConfiguration) -> float:
        """Calculate context relevance score"""
        score = 0.0
        
        # Device context
        device_type = context.get('device_type', 'desktop')
        if experiment.experiment_type == ExperimentType.INTERFACE_LAYOUT:
            if device_type == 'mobile':
                score += 0.3
            elif device_type == 'desktop':
                score += 0.2
        
        # Time context
        hour = datetime.utcnow().hour
        if 9 <= hour <= 17:  # Work hours
            score += 0.2
        
        # User experience level
        experience = context.get('experience_level', 'intermediate')
        if experience == 'beginner' and experiment.experiment_type == ExperimentType.ONBOARDING_FLOW:
            score += 0.4
        
        return score
    
    def _calculate_variant_context_fit(self, variant: ExperimentVariant, context: Dict[str, Any]) -> float:
        """Calculate how well a variant fits the current context"""
        fit_score = 0.5  # Base score
        
        variant_config = variant.configuration
        
        # Device type fit
        device_type = context.get('device_type', 'desktop')
        if 'layout_density' in variant_config:
            if device_type == 'mobile' and variant_config['layout_density'] == 'high':
                fit_score -= 0.2
            elif device_type == 'desktop' and variant_config['layout_density'] == 'low':
                fit_score -= 0.1
        
        # Experience level fit
        experience = context.get('experience_level', 'intermediate')
        if 'complexity' in variant_config:
            if experience == 'beginner' and variant_config.get('complexity') == 'high':
                fit_score -= 0.3
            elif experience == 'expert' and variant_config.get('complexity') == 'low':
                fit_score -= 0.2
        
        return max(0.0, min(1.0, fit_score))
    
    def _bandit_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                          context: Dict[str, Any]) -> str:
        """Multi-armed bandit allocation"""
        experiment_id = experiment.experiment_id
        
        if experiment_id not in self.bandit_models:
            # Initialize bandit model
            self.bandit_models[experiment_id] = {
                'variant_rewards': defaultdict(list),
                'variant_counts': defaultdict(int),
                'epsilon': 0.1  # Exploration rate
            }
        
        bandit = self.bandit_models[experiment_id]
        
        # Epsilon-greedy strategy
        import random
        if random.random() < bandit['epsilon']:
            # Explore: random variant
            active_variants = [v for v in experiment.variants if v.active]
            return random.choice(active_variants).variant_id
        else:
            # Exploit: best performing variant
            best_variant = None
            best_avg_reward = -float('inf')
            
            for variant in experiment.variants:
                if not variant.active:
                    continue
                    
                rewards = bandit['variant_rewards'][variant.variant_id]
                if rewards:
                    avg_reward = np.mean(rewards)
                    if avg_reward > best_avg_reward:
                        best_avg_reward = avg_reward
                        best_variant = variant
            
            if best_variant:
                return best_variant.variant_id
            else:
                # No data yet, random allocation
                return self._random_allocation(user_id, experiment, context)
    
    def _bayesian_allocation(self, user_id: str, experiment: ExperimentConfiguration,
                           context: Dict[str, Any]) -> str:
        """Bayesian optimization allocation"""
        # Simplified Bayesian allocation
        # In practice, would use more sophisticated Bayesian optimization
        return self._adaptive_allocation(user_id, experiment, context)
    
    def update_bandit_reward(self, experiment_id: str, variant_id: str, reward: float):
        """Update bandit model with reward feedback"""
        if experiment_id in self.bandit_models:
            bandit = self.bandit_models[experiment_id]
            bandit['variant_rewards'][variant_id].append(reward)
            bandit['variant_counts'][variant_id] += 1
            
            # Decay epsilon over time (reduce exploration)
            total_counts = sum(bandit['variant_counts'].values())
            bandit['epsilon'] = max(0.01, 0.1 / (1 + total_counts / 1000))
    
    def get_allocation_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get allocation summary for an experiment"""
        assignments = self.allocation_history.get(experiment_id, [])
        
        if not assignments:
            return {"total_assignments": 0, "variant_distribution": {}}
        
        variant_counts = defaultdict(int)
        for assignment in assignments:
            variant_counts[assignment.variant_id] += 1
        
        total = len(assignments)
        variant_distribution = {
            variant_id: {"count": count, "percentage": (count / total) * 100}
            for variant_id, count in variant_counts.items()
        }
        
        return {
            "total_assignments": total,
            "variant_distribution": variant_distribution,
            "first_assignment": assignments[0].assigned_at.isoformat(),
            "last_assignment": assignments[-1].assigned_at.isoformat()
        }

class StatisticalAnalyzer:
    """Statistical analysis engine for A/B test results"""
    
    def __init__(self):
        self.analysis_methods = {
            StatisticalTest.T_TEST: self._t_test_analysis,
            StatisticalTest.CHI_SQUARE: self._chi_square_analysis,
            StatisticalTest.MANN_WHITNEY: self._mann_whitney_analysis,
            StatisticalTest.ANOVA: self._anova_analysis,
            StatisticalTest.BAYESIAN: self._bayesian_analysis,
            StatisticalTest.BOOTSTRAP: self._bootstrap_analysis
        }
        self.logger = logging.getLogger(__name__)
    
    def analyze_experiment(self, experiment: ExperimentConfiguration,
                          events: List[ExperimentEvent]) -> List[ExperimentResult]:
        """Analyze experiment results"""
        results = []
        
        # Group events by metric and variant
        metric_data = defaultdict(lambda: defaultdict(list))
        for event in events:
            metric_data[event.metric_id][event.variant_id].append(event.value)
        
        # Analyze each metric
        for metric in experiment.metrics:
            metric_results = self._analyze_metric(metric, metric_data[metric.metric_id])
            results.extend(metric_results)
        
        return results
    
    def _analyze_metric(self, metric: ExperimentMetric, 
                       variant_data: Dict[str, List[Union[float, int, bool]]]) -> List[ExperimentResult]:
        """Analyze a single metric across variants"""
        results = []
        
        if len(variant_data) < 2:
            self.logger.warning(f"Insufficient variants for metric {metric.metric_id}")
            return results
        
        # Get analysis method
        analysis_func = self.analysis_methods.get(metric.statistical_test, self._t_test_analysis)
        
        # Convert data to appropriate format
        processed_data = {}
        for variant_id, values in variant_data.items():
            if metric.data_type == 'binary':
                # Convert boolean values to 0/1
                processed_values = [1 if v else 0 for v in values]
            else:
                processed_values = [float(v) for v in values]
            
            processed_data[variant_id] = processed_values
        
        # Perform statistical analysis
        try:
            variant_results = analysis_func(metric, processed_data)
            results.extend(variant_results)
        except Exception as e:
            self.logger.error(f"Error analyzing metric {metric.metric_id}: {e}")
        
        return results
    
    def _t_test_analysis(self, metric: ExperimentMetric, 
                        variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform t-test analysis"""
        results = []
        variant_ids = list(variant_data.keys())
        
        # Find control variant
        control_id = None
        for variant_id in variant_ids:
            if 'control' in variant_id.lower():
                control_id = variant_id
                break
        
        if not control_id:
            control_id = variant_ids[0]  # Use first variant as control
        
        control_data = variant_data[control_id]
        
        for variant_id in variant_ids:
            test_data = variant_data[variant_id]
            
            if len(test_data) == 0 or len(control_data) == 0:
                continue
            
            # Calculate basic statistics
            mean_val = np.mean(test_data)
            std_val = np.std(test_data, ddof=1) if len(test_data) > 1 else 0
            
            # Calculate confidence interval
            confidence_interval = self._calculate_confidence_interval(test_data, 0.95)
            
            # Perform t-test if comparing with different variant
            p_value = None
            effect_size = None
            statistical_significance = False
            
            if variant_id != control_id and len(control_data) > 1 and len(test_data) > 1:
                try:
                    t_stat, p_value = stats.ttest_ind(test_data, control_data)
                    statistical_significance = p_value < metric.significance_level
                    
                    # Calculate Cohen's d
                    pooled_std = np.sqrt((np.var(test_data, ddof=1) + np.var(control_data, ddof=1)) / 2)
                    if pooled_std > 0:
                        effect_size = abs(np.mean(test_data) - np.mean(control_data)) / pooled_std
                    
                except Exception as e:
                    self.logger.warning(f"T-test failed for {variant_id}: {e}")
            
            # Check practical significance
            practical_significance = False
            if effect_size is not None:
                practical_significance = effect_size >= metric.minimum_effect_size
            
            result = ExperimentResult(
                metric_id=metric.metric_id,
                variant_id=variant_id,
                sample_size=len(test_data),
                mean=mean_val,
                std_dev=std_val,
                confidence_interval=confidence_interval,
                p_value=p_value,
                effect_size=effect_size,
                statistical_significance=statistical_significance,
                practical_significance=practical_significance
            )
            
            results.append(result)
        
        return results
    
    def _chi_square_analysis(self, metric: ExperimentMetric,
                           variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform chi-square analysis for binary/categorical data"""
        results = []
        
        # Create contingency table
        variant_ids = list(variant_data.keys())
        contingency_table = []
        
        for variant_id in variant_ids:
            data = variant_data[variant_id]
            successes = sum(data)
            failures = len(data) - successes
            contingency_table.append([successes, failures])
        
        contingency_table = np.array(contingency_table)
        
        if contingency_table.size == 0:
            return results
        
        try:
            chi2_stat, p_value, dof, expected = stats.chi2_contingency(contingency_table)
            
            # Calculate results for each variant
            for i, variant_id in enumerate(variant_ids):
                data = variant_data[variant_id]
                
                if len(data) == 0:
                    continue
                
                mean_val = np.mean(data)  # Proportion for binary data
                std_val = np.sqrt(mean_val * (1 - mean_val)) if mean_val not in [0, 1] else 0
                
                # Confidence interval for proportion
                confidence_interval = self._calculate_proportion_confidence_interval(
                    sum(data), len(data), 0.95
                )
                
                result = ExperimentResult(
                    metric_id=metric.metric_id,
                    variant_id=variant_id,
                    sample_size=len(data),
                    mean=mean_val,
                    std_dev=std_val,
                    confidence_interval=confidence_interval,
                    p_value=p_value,
                    statistical_significance=p_value < metric.significance_level
                )
                
                results.append(result)
        
        except Exception as e:
            self.logger.error(f"Chi-square analysis failed: {e}")
        
        return results
    
    def _mann_whitney_analysis(self, metric: ExperimentMetric,
                             variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform Mann-Whitney U test (non-parametric)"""
        results = []
        variant_ids = list(variant_data.keys())
        
        if len(variant_ids) < 2:
            return results
        
        # Use first variant as control
        control_id = variant_ids[0]
        control_data = variant_data[control_id]
        
        for variant_id in variant_ids:
            test_data = variant_data[variant_id]
            
            if len(test_data) == 0:
                continue
            
            mean_val = np.mean(test_data)
            std_val = np.std(test_data, ddof=1) if len(test_data) > 1 else 0
            confidence_interval = self._calculate_confidence_interval(test_data, 0.95)
            
            p_value = None
            statistical_significance = False
            
            if variant_id != control_id and len(control_data) > 0 and len(test_data) > 0:
                try:
                    u_stat, p_value = stats.mannwhitneyu(test_data, control_data, alternative='two-sided')
                    statistical_significance = p_value < metric.significance_level
                except Exception as e:
                    self.logger.warning(f"Mann-Whitney test failed for {variant_id}: {e}")
            
            result = ExperimentResult(
                metric_id=metric.metric_id,
                variant_id=variant_id,
                sample_size=len(test_data),
                mean=mean_val,
                std_dev=std_val,
                confidence_interval=confidence_interval,
                p_value=p_value,
                statistical_significance=statistical_significance
            )
            
            results.append(result)
        
        return results
    
    def _anova_analysis(self, metric: ExperimentMetric,
                       variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform ANOVA analysis"""
        results = []
        
        # Prepare data for ANOVA
        groups = [data for data in variant_data.values() if len(data) > 0]
        
        if len(groups) < 2:
            return results
        
        try:
            f_stat, p_value = stats.f_oneway(*groups)
            
            # Create results for each variant
            for variant_id, data in variant_data.items():
                if len(data) == 0:
                    continue
                
                mean_val = np.mean(data)
                std_val = np.std(data, ddof=1) if len(data) > 1 else 0
                confidence_interval = self._calculate_confidence_interval(data, 0.95)
                
                result = ExperimentResult(
                    metric_id=metric.metric_id,
                    variant_id=variant_id,
                    sample_size=len(data),
                    mean=mean_val,
                    std_dev=std_val,
                    confidence_interval=confidence_interval,
                    p_value=p_value,
                    statistical_significance=p_value < metric.significance_level
                )
                
                results.append(result)
        
        except Exception as e:
            self.logger.error(f"ANOVA analysis failed: {e}")
        
        return results
    
    def _bayesian_analysis(self, metric: ExperimentMetric,
                          variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform Bayesian analysis"""
        # Simplified Bayesian analysis
        # In practice, would use more sophisticated Bayesian methods
        return self._t_test_analysis(metric, variant_data)
    
    def _bootstrap_analysis(self, metric: ExperimentMetric,
                           variant_data: Dict[str, List[float]]) -> List[ExperimentResult]:
        """Perform bootstrap analysis"""
        results = []
        
        for variant_id, data in variant_data.items():
            if len(data) == 0:
                continue
            
            # Bootstrap resampling
            n_bootstrap = 1000
            bootstrap_means = []
            
            for _ in range(n_bootstrap):
                bootstrap_sample = np.random.choice(data, size=len(data), replace=True)
                bootstrap_means.append(np.mean(bootstrap_sample))
            
            mean_val = np.mean(data)
            std_val = np.std(bootstrap_means)  # Bootstrap standard error
            
            # Bootstrap confidence interval
            confidence_interval = (
                np.percentile(bootstrap_means, 2.5),
                np.percentile(bootstrap_means, 97.5)
            )
            
            result = ExperimentResult(
                metric_id=metric.metric_id,
                variant_id=variant_id,
                sample_size=len(data),
                mean=mean_val,
                std_dev=std_val,
                confidence_interval=confidence_interval
            )
            
            results.append(result)
        
        return results
    
    def _calculate_confidence_interval(self, data: List[float], confidence: float) -> Tuple[float, float]:
        """Calculate confidence interval for mean"""
        if len(data) <= 1:
            mean_val = np.mean(data) if data else 0
            return (mean_val, mean_val)
        
        mean_val = np.mean(data)
        std_err = stats.sem(data)
        
        # Use t-distribution for small samples
        if len(data) < 30:
            t_critical = stats.t.ppf((1 + confidence) / 2, len(data) - 1)
            margin_error = t_critical * std_err
        else:
            z_critical = stats.norm.ppf((1 + confidence) / 2)
            margin_error = z_critical * std_err
        
        return (mean_val - margin_error, mean_val + margin_error)
    
    def _calculate_proportion_confidence_interval(self, successes: int, total: int, 
                                                confidence: float) -> Tuple[float, float]:
        """Calculate confidence interval for proportion"""
        if total == 0:
            return (0.0, 0.0)
        
        p = successes / total
        
        # Wilson score interval (more robust than normal approximation)
        z = stats.norm.ppf((1 + confidence) / 2)
        
        denominator = 1 + (z**2) / total
        center = (p + (z**2) / (2 * total)) / denominator
        margin = z * np.sqrt((p * (1 - p) + (z**2) / (4 * total)) / total) / denominator
        
        return (max(0, center - margin), min(1, center + margin))

class IntelligentABTestingFramework:
    """
    Main intelligent A/B testing framework
    """
    
    def __init__(self):
        self.experiment_designer = ExperimentDesigner()
        self.traffic_allocator = TrafficAllocator()
        self.statistical_analyzer = StatisticalAnalyzer()
        
        self.experiments: Dict[str, ExperimentConfiguration] = {}
        self.experiment_events: Dict[str, List[ExperimentEvent]] = defaultdict(list)
        
        # Real-time monitoring
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        self.logger = logging.getLogger(__name__)
    
    def create_experiment(self, experiment_type: ExperimentType,
                         objectives: List[str],
                         constraints: Dict[str, Any] = None) -> ExperimentConfiguration:
        """Create a new A/B test experiment"""
        experiment = self.experiment_designer.design_experiment(
            experiment_type, objectives, constraints
        )
        
        self.experiments[experiment.experiment_id] = experiment
        self.logger.info(f"Created experiment {experiment.experiment_id}")
        
        return experiment
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an A/B test experiment"""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        
        if experiment.status != ExperimentStatus.READY:
            self.logger.warning(f"Experiment {experiment_id} is not ready to start")
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = datetime.utcnow()
        
        self.logger.info(f"Started experiment {experiment_id}")
        return True
    
    def stop_experiment(self, experiment_id: str, reason: str = "") -> bool:
        """Stop a running experiment"""
        if experiment_id not in self.experiments:
            return False
        
        experiment = self.experiments[experiment_id]
        
        if experiment.status != ExperimentStatus.RUNNING:
            return False
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = datetime.utcnow()
        experiment.conclusion = reason
        
        self.logger.info(f"Stopped experiment {experiment_id}: {reason}")
        return True
    
    def assign_user_to_experiment(self, user_id: str, experiment_id: str,
                                 user_context: Dict[str, Any] = None) -> Optional[str]:
        """Assign user to experiment variant"""
        if experiment_id not in self.experiments:
            return None
        
        experiment = self.experiments[experiment_id]
        
        if experiment.status != ExperimentStatus.RUNNING:
            return None
        
        # Check if user meets target audience criteria
        if not self._user_meets_criteria(user_id, user_context or {}, experiment):
            return None
        
        variant_id = self.traffic_allocator.allocate_user(user_id, experiment, user_context)
        return variant_id
    
    def record_experiment_event(self, user_id: str, experiment_id: str, variant_id: str,
                               metric_id: str, value: Union[float, int, bool],
                               context: Dict[str, Any] = None) -> bool:
        """Record an experiment event"""
        if experiment_id not in self.experiments:
            return False
        
        event = ExperimentEvent(
            event_id=f"{experiment_id}_{user_id}_{datetime.utcnow().isoformat()}",
            user_id=user_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            metric_id=metric_id,
            value=value,
            context=context or {}
        )
        
        self.experiment_events[experiment_id].append(event)
        
        # Update bandit model if using bandit allocation
        experiment = self.experiments[experiment_id]
        if experiment.traffic_allocation_strategy == TrafficAllocation.BANDIT:
            # Convert metric value to reward (simplified)
            reward = float(value) if isinstance(value, (int, float)) else (1.0 if value else 0.0)
            self.traffic_allocator.update_bandit_reward(experiment_id, variant_id, reward)
        
        return True
    
    def analyze_experiment_results(self, experiment_id: str) -> Optional[List[ExperimentResult]]:
        """Analyze experiment results"""
        if experiment_id not in self.experiments:
            return None
        
        experiment = self.experiments[experiment_id]
        events = self.experiment_events[experiment_id]
        
        results = self.statistical_analyzer.analyze_experiment(experiment, events)
        experiment.results = results
        
        # Determine winner if experiment is completed
        if experiment.status == ExperimentStatus.COMPLETED:
            winner = self._determine_winner(experiment, results)
            experiment.winner = winner
        
        return results
    
    def _user_meets_criteria(self, user_id: str, context: Dict[str, Any], 
                           experiment: ExperimentConfiguration) -> bool:
        """Check if user meets experiment criteria"""
        target_audience = experiment.target_audience
        exclusion_criteria = experiment.exclusion_criteria
        
        # Check target audience
        for criterion, required_value in target_audience.items():
            if criterion not in context:
                continue
                
            actual_value = context[criterion]
            
            if isinstance(required_value, list):
                if actual_value not in required_value:
                    return False
            else:
                if actual_value != required_value:
                    return False
        
        # Check exclusion criteria
        for criterion, excluded_value in exclusion_criteria.items():
            if criterion not in context:
                continue
                
            actual_value = context[criterion]
            
            if isinstance(excluded_value, list):
                if actual_value in excluded_value:
                    return False
            else:
                if actual_value == excluded_value:
                    return False
        
        return True
    
    def _determine_winner(self, experiment: ExperimentConfiguration,
                         results: List[ExperimentResult]) -> Optional[str]:
        """Determine winning variant based on results"""
        if not results:
            return None
        
        # Focus on primary metrics
        primary_results = [r for r in results if any(m.metric_type == 'primary' and m.metric_id == r.metric_id for m in experiment.metrics)]
        
        if not primary_results:
            return None
        
        # Find variants with statistically and practically significant improvements
        significant_results = [
            r for r in primary_results 
            if r.statistical_significance and r.practical_significance
        ]
        
        if not significant_results:
            # No clear winner
            return None
        
        # Choose variant with best performance on primary metrics
        best_variant = None
        best_score = -float('inf')
        
        variant_scores = defaultdict(list)
        for result in significant_results:
            # Higher mean is better for most metrics
            metric = next(m for m in experiment.metrics if m.metric_id == result.metric_id)
            
            score = result.mean
            if metric.goal == 'decrease':
                score = -score
            
            variant_scores[result.variant_id].append(score)
        
        # Calculate average score per variant
        for variant_id, scores in variant_scores.items():
            avg_score = np.mean(scores)
            if avg_score > best_score:
                best_score = avg_score
                best_variant = variant_id
        
        return best_variant
    
    def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """Get comprehensive experiment summary"""
        if experiment_id not in self.experiments:
            return {"error": "Experiment not found"}
        
        experiment = self.experiments[experiment_id]
        events = self.experiment_events[experiment_id]
        
        # Basic experiment info
        summary = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "description": experiment.description,
            "type": experiment.experiment_type.value,
            "status": experiment.status.value,
            "created_at": experiment.created_at.isoformat(),
            "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
            "ended_at": experiment.ended_at.isoformat() if experiment.ended_at else None
        }
        
        # Variants info
        summary["variants"] = [
            {
                "variant_id": v.variant_id,
                "name": v.name,
                "description": v.description,
                "traffic_allocation": v.traffic_allocation,
                "is_control": v.is_control
            }
            for v in experiment.variants
        ]
        
        # Metrics info
        summary["metrics"] = [
            {
                "metric_id": m.metric_id,
                "name": m.name,
                "type": m.metric_type,
                "data_type": m.data_type,
                "goal": m.goal
            }
            for m in experiment.metrics
        ]
        
        # Traffic allocation summary
        allocation_summary = self.traffic_allocator.get_allocation_summary(experiment_id)
        summary["traffic_allocation"] = allocation_summary
        
        # Events summary
        summary["events"] = {
            "total_events": len(events),
            "unique_users": len(set(e.user_id for e in events)),
            "events_by_variant": dict(Counter(e.variant_id for e in events)),
            "events_by_metric": dict(Counter(e.metric_id for e in events))
        }
        
        # Results (if analyzed)
        if experiment.results:
            summary["results"] = [asdict(result) for result in experiment.results]
            summary["winner"] = experiment.winner
            summary["conclusion"] = experiment.conclusion
        
        # Duration info
        if experiment.started_at:
            duration = (experiment.ended_at or datetime.utcnow()) - experiment.started_at
            summary["duration_days"] = duration.days
            summary["duration_hours"] = duration.total_seconds() / 3600
        
        return summary
    
    def get_active_experiments(self) -> List[Dict[str, Any]]:
        """Get list of active experiments"""
        active_experiments = []
        
        for experiment in self.experiments.values():
            if experiment.status == ExperimentStatus.RUNNING:
                active_experiments.append({
                    "experiment_id": experiment.experiment_id,
                    "name": experiment.name,
                    "type": experiment.experiment_type.value,
                    "started_at": experiment.started_at.isoformat(),
                    "variants_count": len(experiment.variants),
                    "metrics_count": len(experiment.metrics)
                })
        
        return active_experiments
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get A/B testing system status"""
        total_experiments = len(self.experiments)
        status_counts = Counter(exp.status.value for exp in self.experiments.values())
        
        return {
            "total_experiments": total_experiments,
            "experiments_by_status": dict(status_counts),
            "total_events": sum(len(events) for events in self.experiment_events.values()),
            "monitoring_active": self.monitoring_active,
            "system_health": "healthy"
        }