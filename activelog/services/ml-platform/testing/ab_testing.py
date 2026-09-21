#!/usr/bin/env python3
"""
ActiveLog ML Platform - A/B Testing Framework
Comprehensive A/B testing for ML models with statistical analysis
"""

import asyncio
import json
import logging
import time
import uuid
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from enum import Enum
import numpy as np
import random
from scipy import stats

logger = logging.getLogger(__name__)

class ExperimentStatus(Enum):
    """A/B experiment status"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TrafficSplitType(Enum):
    """Traffic splitting strategies"""
    RANDOM = "random"
    USER_ID = "user_id"
    SESSION_ID = "session_id"
    FEATURE_BASED = "feature_based"
    TIME_BASED = "time_based"

@dataclass
class ExperimentVariant:
    """A/B test variant configuration"""
    variant_id: str
    name: str
    model_id: str
    traffic_percentage: float
    description: str = ""
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}

@dataclass
class Experiment:
    """A/B testing experiment"""
    experiment_id: str
    name: str
    description: str
    variants: List[ExperimentVariant]
    status: ExperimentStatus = ExperimentStatus.DRAFT
    traffic_split_type: TrafficSplitType = TrafficSplitType.RANDOM
    primary_metric: str = "conversion_rate"
    secondary_metrics: List[str] = None
    minimum_sample_size: int = 1000
    significance_level: float = 0.05
    power: float = 0.8
    created_by: str = ""
    created_at: float = 0
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.secondary_metrics is None:
            self.secondary_metrics = []
        if self.tags is None:
            self.tags = []
        if self.created_at == 0:
            self.created_at = time.time()

@dataclass
class ExperimentEvent:
    """Individual experiment event/measurement"""
    event_id: str
    experiment_id: str
    variant_id: str
    user_id: str
    session_id: str
    event_type: str  # "exposure", "conversion", "custom"
    metrics: Dict[str, float]
    metadata: Dict[str, Any] = None
    timestamp: float = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class ExperimentResults:
    """A/B test statistical results"""
    experiment_id: str
    variant_results: Dict[str, Dict[str, Any]]
    statistical_significance: Dict[str, bool]
    confidence_intervals: Dict[str, Dict[str, Tuple[float, float]]]
    p_values: Dict[str, float]
    effect_sizes: Dict[str, float]
    sample_sizes: Dict[str, int]
    conversion_rates: Dict[str, float]
    recommendation: str
    computed_at: float = 0
    
    def __post_init__(self):
        if self.computed_at == 0:
            self.computed_at = time.time()

class TrafficSplitter:
    """Traffic splitting logic for A/B tests"""
    
    @staticmethod
    def assign_variant(user_id: str, session_id: str, experiment: Experiment, 
                      features: Dict[str, Any] = None) -> str:
        """Assign user to experiment variant"""
        
        if experiment.traffic_split_type == TrafficSplitType.RANDOM:
            return TrafficSplitter._random_assignment(experiment)
        
        elif experiment.traffic_split_type == TrafficSplitType.USER_ID:
            return TrafficSplitter._user_id_assignment(user_id, experiment)
        
        elif experiment.traffic_split_type == TrafficSplitType.SESSION_ID:
            return TrafficSplitter._session_id_assignment(session_id, experiment)
        
        elif experiment.traffic_split_type == TrafficSplitType.FEATURE_BASED:
            return TrafficSplitter._feature_based_assignment(features or {}, experiment)
        
        elif experiment.traffic_split_type == TrafficSplitType.TIME_BASED:
            return TrafficSplitter._time_based_assignment(experiment)
        
        else:
            return TrafficSplitter._random_assignment(experiment)
    
    @staticmethod
    def _random_assignment(experiment: Experiment) -> str:
        """Random variant assignment"""
        rand = random.random() * 100
        cumulative = 0
        
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if rand <= cumulative:
                return variant.variant_id
        
        # Fallback to first variant
        return experiment.variants[0].variant_id if experiment.variants else ""
    
    @staticmethod
    def _user_id_assignment(user_id: str, experiment: Experiment) -> str:
        """Consistent user-based assignment"""
        # Use hash of user_id + experiment_id for consistency
        hash_input = f"{user_id}_{experiment.experiment_id}"
        hash_value = hash(hash_input) % 10000
        percentage = hash_value / 100.0
        
        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if percentage <= cumulative:
                return variant.variant_id
        
        return experiment.variants[0].variant_id if experiment.variants else ""
    
    @staticmethod
    def _session_id_assignment(session_id: str, experiment: Experiment) -> str:
        """Session-based assignment"""
        hash_input = f"{session_id}_{experiment.experiment_id}"
        hash_value = hash(hash_input) % 10000
        percentage = hash_value / 100.0
        
        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if percentage <= cumulative:
                return variant.variant_id
        
        return experiment.variants[0].variant_id if experiment.variants else ""
    
    @staticmethod
    def _feature_based_assignment(features: Dict[str, Any], experiment: Experiment) -> str:
        """Feature-based assignment (simplified)"""
        # Simple feature-based logic - can be made more sophisticated
        feature_score = sum(hash(str(v)) % 100 for v in features.values()) % 100
        
        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if feature_score <= cumulative:
                return variant.variant_id
        
        return experiment.variants[0].variant_id if experiment.variants else ""
    
    @staticmethod
    def _time_based_assignment(experiment: Experiment) -> str:
        """Time-based assignment"""
        # Assign based on current time (for temporal experiments)
        time_factor = (time.time() % 86400) / 864  # Current time of day as percentage
        
        cumulative = 0
        for variant in experiment.variants:
            cumulative += variant.traffic_percentage
            if time_factor <= cumulative:
                return variant.variant_id
        
        return experiment.variants[0].variant_id if experiment.variants else ""

class StatisticalAnalyzer:
    """Statistical analysis for A/B test results"""
    
    @staticmethod
    def analyze_experiment(experiment: Experiment, events: List[ExperimentEvent]) -> ExperimentResults:
        """Perform comprehensive statistical analysis"""
        
        # Group events by variant
        variant_data = defaultdict(list)
        for event in events:
            variant_data[event.variant_id].append(event)
        
        # Calculate basic metrics
        variant_results = {}
        sample_sizes = {}
        conversion_rates = {}
        
        for variant_id, variant_events in variant_data.items():
            # Basic metrics
            total_events = len(variant_events)
            conversions = len([e for e in variant_events if e.event_type == "conversion"])
            conversion_rate = conversions / total_events if total_events > 0 else 0
            
            # Custom metrics aggregation
            custom_metrics = defaultdict(list)
            for event in variant_events:
                for metric, value in event.metrics.items():
                    custom_metrics[metric].append(value)
            
            aggregated_metrics = {}
            for metric, values in custom_metrics.items():
                if values:
                    aggregated_metrics[f"{metric}_mean"] = np.mean(values)
                    aggregated_metrics[f"{metric}_std"] = np.std(values)
                    aggregated_metrics[f"{metric}_median"] = np.median(values)
                    aggregated_metrics[f"{metric}_95th"] = np.percentile(values, 95)
            
            variant_results[variant_id] = {
                "total_events": total_events,
                "conversions": conversions,
                "conversion_rate": conversion_rate,
                "custom_metrics": aggregated_metrics
            }
            
            sample_sizes[variant_id] = total_events
            conversion_rates[variant_id] = conversion_rate
        
        # Statistical significance testing
        statistical_significance = {}
        p_values = {}
        effect_sizes = {}
        confidence_intervals = {}
        
        if len(variant_results) >= 2:
            variants = list(variant_results.keys())
            control_variant = variants[0]  # Assume first variant is control
            
            for variant_id in variants[1:]:
                # Perform two-proportion z-test for conversion rates
                control_conversions = variant_results[control_variant]["conversions"]
                control_total = variant_results[control_variant]["total_events"]
                
                test_conversions = variant_results[variant_id]["conversions"]
                test_total = variant_results[variant_id]["total_events"]
                
                if control_total > 0 and test_total > 0:
                    # Two-proportion z-test
                    p_value, effect_size, ci = StatisticalAnalyzer._two_proportion_test(
                        control_conversions, control_total,
                        test_conversions, test_total
                    )
                    
                    statistical_significance[f"{control_variant}_vs_{variant_id}"] = p_value < experiment.significance_level
                    p_values[f"{control_variant}_vs_{variant_id}"] = p_value
                    effect_sizes[f"{control_variant}_vs_{variant_id}"] = effect_size
                    confidence_intervals[f"{control_variant}_vs_{variant_id}"] = ci
        
        # Generate recommendation
        recommendation = StatisticalAnalyzer._generate_recommendation(
            experiment, variant_results, statistical_significance, p_values
        )
        
        return ExperimentResults(
            experiment_id=experiment.experiment_id,
            variant_results=variant_results,
            statistical_significance=statistical_significance,
            confidence_intervals=confidence_intervals,
            p_values=p_values,
            effect_sizes=effect_sizes,
            sample_sizes=sample_sizes,
            conversion_rates=conversion_rates,
            recommendation=recommendation
        )
    
    @staticmethod
    def _two_proportion_test(control_successes: int, control_total: int,
                           test_successes: int, test_total: int) -> Tuple[float, float, Tuple[float, float]]:
        """Perform two-proportion z-test"""
        
        # Calculate proportions
        p1 = control_successes / control_total
        p2 = test_successes / test_total
        
        # Calculate pooled proportion
        p_pooled = (control_successes + test_successes) / (control_total + test_total)
        
        # Calculate standard error
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/control_total + 1/test_total))
        
        # Calculate z-score
        z_score = (p2 - p1) / se if se > 0 else 0
        
        # Calculate p-value (two-tailed)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        
        # Calculate effect size (Cohen's h)
        effect_size = 2 * (np.arcsin(np.sqrt(p2)) - np.arcsin(np.sqrt(p1)))
        
        # Calculate confidence interval for difference in proportions
        diff = p2 - p1
        se_diff = np.sqrt(p1*(1-p1)/control_total + p2*(1-p2)/test_total)
        ci_lower = diff - 1.96 * se_diff
        ci_upper = diff + 1.96 * se_diff
        
        return p_value, effect_size, (ci_lower, ci_upper)
    
    @staticmethod
    def _generate_recommendation(experiment: Experiment, variant_results: Dict[str, Any],
                               statistical_significance: Dict[str, bool],
                               p_values: Dict[str, float]) -> str:
        """Generate experiment recommendation"""
        
        if not variant_results:
            return "Insufficient data for analysis"
        
        if len(variant_results) < 2:
            return "Need at least 2 variants for comparison"
        
        # Check sample sizes
        min_sample_size = min(result["total_events"] for result in variant_results.values())
        if min_sample_size < experiment.minimum_sample_size:
            return f"Insufficient sample size. Need at least {experiment.minimum_sample_size} samples per variant."
        
        # Find best performing variant
        best_variant = max(variant_results.keys(), 
                          key=lambda v: variant_results[v]["conversion_rate"])
        
        # Check if best variant is statistically significant
        significant_results = [k for k, v in statistical_significance.items() if v]
        
        if significant_results:
            return f"✅ Significant results found. Recommend variant {best_variant} " \
                   f"(conversion rate: {variant_results[best_variant]['conversion_rate']:.2%})"
        else:
            return f"⚠️ No statistically significant differences found. " \
                   f"Consider running longer or increasing sample size."

class ABTestingFramework:
    """Main A/B testing framework"""
    
    def __init__(self, db_path: str = "ab_testing.db"):
        self.db_path = db_path
        
        # Database connection
        self.db_lock = threading.Lock()
        self._init_database()
        
        # In-memory caches
        self.experiments: Dict[str, Experiment] = {}
        self.active_experiments: Dict[str, Experiment] = {}
        
        # Components
        self.traffic_splitter = TrafficSplitter()
        self.statistical_analyzer = StatisticalAnalyzer()
        
        # Statistics
        self.stats = {
            "total_experiments": 0,
            "active_experiments": 0,
            "completed_experiments": 0,
            "total_events": 0,
            "events_today": 0
        }
        
        # Load existing experiments
        self._load_experiments()
    
    def _init_database(self):
        """Initialize SQLite database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Experiments table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    variants TEXT,
                    status TEXT,
                    traffic_split_type TEXT,
                    primary_metric TEXT,
                    secondary_metrics TEXT,
                    minimum_sample_size INTEGER,
                    significance_level REAL,
                    power REAL,
                    created_by TEXT,
                    created_at REAL,
                    started_at REAL,
                    ended_at REAL,
                    tags TEXT,
                    INDEX(status),
                    INDEX(created_at)
                )
            """)
            
            # Events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_events (
                    event_id TEXT PRIMARY KEY,
                    experiment_id TEXT NOT NULL,
                    variant_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    metrics TEXT,
                    metadata TEXT,
                    timestamp REAL,
                    INDEX(experiment_id),
                    INDEX(variant_id),
                    INDEX(user_id),
                    INDEX(timestamp)
                )
            """)
            
            # Results cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    experiment_id TEXT PRIMARY KEY,
                    results_data TEXT,
                    computed_at REAL,
                    INDEX(computed_at)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def _load_experiments(self):
        """Load existing experiments from database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("SELECT * FROM experiments")
                
                for row in cursor.fetchall():
                    experiment = self._row_to_experiment(row)
                    self.experiments[experiment.experiment_id] = experiment
                    
                    if experiment.status == ExperimentStatus.RUNNING:
                        self.active_experiments[experiment.experiment_id] = experiment
                
                self.stats["total_experiments"] = len(self.experiments)
                self.stats["active_experiments"] = len(self.active_experiments)
                
                conn.close()
                
                logger.info(f"Loaded {len(self.experiments)} experiments from database")
                
        except sqlite3.Error as e:
            logger.error(f"Error loading experiments: {e}")
    
    def create_experiment(self, name: str, description: str, variants: List[ExperimentVariant],
                         primary_metric: str = "conversion_rate", **kwargs) -> str:
        """Create new A/B test experiment"""
        
        # Validate traffic percentages sum to 100
        total_traffic = sum(v.traffic_percentage for v in variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Traffic percentages must sum to 100%, got {total_traffic}%")
        
        experiment = Experiment(
            experiment_id=str(uuid.uuid4()),
            name=name,
            description=description,
            variants=variants,
            primary_metric=primary_metric,
            **kwargs
        )
        
        # Save to database
        self._save_experiment(experiment)
        
        # Update cache and stats
        self.experiments[experiment.experiment_id] = experiment
        self.stats["total_experiments"] += 1
        
        logger.info(f"Created experiment: {name} ({experiment.experiment_id})")
        return experiment.experiment_id
    
    def start_experiment(self, experiment_id: str) -> bool:
        """Start an experiment"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False
        
        experiment.status = ExperimentStatus.RUNNING
        experiment.started_at = time.time()
        
        # Update database and caches
        self._save_experiment(experiment)
        self.active_experiments[experiment_id] = experiment
        self.stats["active_experiments"] += 1
        
        logger.info(f"Started experiment: {experiment.name}")
        return True
    
    def stop_experiment(self, experiment_id: str) -> bool:
        """Stop an experiment"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return False
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.ended_at = time.time()
        
        # Update database and caches
        self._save_experiment(experiment)
        if experiment_id in self.active_experiments:
            del self.active_experiments[experiment_id]
            self.stats["active_experiments"] -= 1
            self.stats["completed_experiments"] += 1
        
        logger.info(f"Stopped experiment: {experiment.name}")
        return True
    
    def assign_variant(self, user_id: str, session_id: str, experiment_id: str,
                      features: Dict[str, Any] = None) -> Optional[str]:
        """Assign user to experiment variant"""
        experiment = self.active_experiments.get(experiment_id)
        if not experiment:
            return None
        
        variant_id = self.traffic_splitter.assign_variant(
            user_id, session_id, experiment, features
        )
        
        # Log exposure event
        self.record_event(
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            session_id=session_id,
            event_type="exposure",
            metrics={"exposed": 1.0}
        )
        
        return variant_id
    
    def record_event(self, experiment_id: str, variant_id: str, user_id: str,
                    session_id: str, event_type: str, metrics: Dict[str, float],
                    metadata: Dict[str, Any] = None) -> str:
        """Record experiment event"""
        
        event = ExperimentEvent(
            event_id=str(uuid.uuid4()),
            experiment_id=experiment_id,
            variant_id=variant_id,
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            metrics=metrics,
            metadata=metadata or {}
        )
        
        # Save to database
        self._save_event(event)
        
        # Update stats
        self.stats["total_events"] += 1
        self.stats["events_today"] += 1
        
        return event.event_id
    
    def analyze_experiment(self, experiment_id: str, force_refresh: bool = False) -> Optional[ExperimentResults]:
        """Get experiment analysis results"""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return None
        
        # Check for cached results
        if not force_refresh:
            cached_results = self._get_cached_results(experiment_id)
            if cached_results and (time.time() - cached_results.computed_at) < 3600:  # 1 hour cache
                return cached_results
        
        # Load events for analysis
        events = self._load_experiment_events(experiment_id)
        
        # Perform statistical analysis
        results = self.statistical_analyzer.analyze_experiment(experiment, events)
        
        # Cache results
        self._cache_results(results)
        
        return results
    
    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID"""
        return self.experiments.get(experiment_id)
    
    def list_experiments(self, status: ExperimentStatus = None) -> List[Experiment]:
        """List experiments with optional status filter"""
        experiments = list(self.experiments.values())
        
        if status:
            experiments = [e for e in experiments if e.status == status]
        
        # Sort by creation time (newest first)
        experiments.sort(key=lambda x: x.created_at, reverse=True)
        
        return experiments
    
    def get_experiment_events(self, experiment_id: str, limit: int = 1000) -> List[ExperimentEvent]:
        """Get recent events for an experiment"""
        return self._load_experiment_events(experiment_id, limit)
    
    def _save_experiment(self, experiment: Experiment):
        """Save experiment to database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO experiments 
                (experiment_id, name, description, variants, status, traffic_split_type,
                 primary_metric, secondary_metrics, minimum_sample_size, significance_level,
                 power, created_by, created_at, started_at, ended_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment.experiment_id, experiment.name, experiment.description,
                json.dumps([asdict(v) for v in experiment.variants]),
                experiment.status.value, experiment.traffic_split_type.value,
                experiment.primary_metric, json.dumps(experiment.secondary_metrics),
                experiment.minimum_sample_size, experiment.significance_level,
                experiment.power, experiment.created_by, experiment.created_at,
                experiment.started_at, experiment.ended_at, json.dumps(experiment.tags)
            ))
            conn.commit()
            conn.close()
    
    def _save_event(self, event: ExperimentEvent):
        """Save event to database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO experiment_events 
                (event_id, experiment_id, variant_id, user_id, session_id, event_type,
                 metrics, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.experiment_id, event.variant_id,
                event.user_id, event.session_id, event.event_type,
                json.dumps(event.metrics), json.dumps(event.metadata),
                event.timestamp
            ))
            conn.commit()
            conn.close()
    
    def _load_experiment_events(self, experiment_id: str, limit: int = None) -> List[ExperimentEvent]:
        """Load events for an experiment"""
        events = []
        
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            query = """
                SELECT event_id, experiment_id, variant_id, user_id, session_id,
                       event_type, metrics, metadata, timestamp
                FROM experiment_events 
                WHERE experiment_id = ?
                ORDER BY timestamp DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query, (experiment_id,))
            
            for row in cursor.fetchall():
                event = ExperimentEvent(
                    event_id=row[0],
                    experiment_id=row[1],
                    variant_id=row[2],
                    user_id=row[3],
                    session_id=row[4],
                    event_type=row[5],
                    metrics=json.loads(row[6]) if row[6] else {},
                    metadata=json.loads(row[7]) if row[7] else {},
                    timestamp=row[8]
                )
                events.append(event)
            
            conn.close()
        
        return events
    
    def _cache_results(self, results: ExperimentResults):
        """Cache experiment results"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO experiment_results 
                (experiment_id, results_data, computed_at)
                VALUES (?, ?, ?)
            """, (
                results.experiment_id,
                json.dumps(asdict(results), default=str),
                results.computed_at
            ))
            conn.commit()
            conn.close()
    
    def _get_cached_results(self, experiment_id: str) -> Optional[ExperimentResults]:
        """Get cached experiment results"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT results_data, computed_at 
                FROM experiment_results 
                WHERE experiment_id = ?
            """, (experiment_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                results_data = json.loads(row[0])
                # Reconstruct ExperimentResults object
                return ExperimentResults(**results_data)
        
        return None
    
    def _row_to_experiment(self, row) -> Experiment:
        """Convert database row to Experiment object"""
        variants_data = json.loads(row[3]) if row[3] else []
        variants = [ExperimentVariant(**v) for v in variants_data]
        
        return Experiment(
            experiment_id=row[0],
            name=row[1],
            description=row[2] or "",
            variants=variants,
            status=ExperimentStatus(row[4]) if row[4] else ExperimentStatus.DRAFT,
            traffic_split_type=TrafficSplitType(row[5]) if row[5] else TrafficSplitType.RANDOM,
            primary_metric=row[6] or "conversion_rate",
            secondary_metrics=json.loads(row[7]) if row[7] else [],
            minimum_sample_size=row[8] or 1000,
            significance_level=row[9] or 0.05,
            power=row[10] or 0.8,
            created_by=row[11] or "",
            created_at=row[12] or 0,
            started_at=row[13],
            ended_at=row[14],
            tags=json.loads(row[15]) if row[15] else []
        )
    
    def get_framework_stats(self) -> Dict[str, Any]:
        """Get A/B testing framework statistics"""
        return {
            **self.stats,
            "experiments_by_status": {
                status.value: len([e for e in self.experiments.values() if e.status == status])
                for status in ExperimentStatus
            },
            "average_experiment_duration": self._calculate_average_duration(),
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_average_duration(self) -> float:
        """Calculate average experiment duration"""
        completed_experiments = [
            e for e in self.experiments.values() 
            if e.status == ExperimentStatus.COMPLETED and e.started_at and e.ended_at
        ]
        
        if not completed_experiments:
            return 0.0
        
        durations = [e.ended_at - e.started_at for e in completed_experiments]
        return sum(durations) / len(durations) / 86400  # Convert to days
    
    def _calculate_success_rate(self) -> float:
        """Calculate percentage of experiments with significant results"""
        completed_experiments = [
            e for e in self.experiments.values() 
            if e.status == ExperimentStatus.COMPLETED
        ]
        
        if not completed_experiments:
            return 0.0
        
        significant_count = 0
        for experiment in completed_experiments:
            results = self._get_cached_results(experiment.experiment_id)
            if results and any(results.statistical_significance.values()):
                significant_count += 1
        
        return (significant_count / len(completed_experiments)) * 100