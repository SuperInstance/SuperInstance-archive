"""
Community Learning Network for Adaptive UX System

This module provides a collaborative platform for sharing successful configurations,
hardware compatibility data, performance benchmarks, user reviews, and expert knowledge
to continuously improve the adaptive UX system across all users.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from collections import defaultdict, Counter
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigurationType(Enum):
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"
    PRODUCTIVITY = "productivity"
    GAMING = "gaming"
    CREATIVE = "creative"
    ENTERPRISE = "enterprise"
    EDUCATIONAL = "educational"
    MOBILE = "mobile"

class ReviewRating(Enum):
    EXCELLENT = 5
    GOOD = 4
    AVERAGE = 3
    POOR = 2
    TERRIBLE = 1

class ContributionType(Enum):
    CONFIGURATION_SHARE = "configuration_share"
    HARDWARE_COMPATIBILITY = "hardware_compatibility"
    PERFORMANCE_BENCHMARK = "performance_benchmark"
    REVIEW = "review"
    TROUBLESHOOTING = "troubleshooting"
    FEATURE_REQUEST = "feature_request"
    BETA_FEEDBACK = "beta_feedback"
    OPTIMIZATION_TIP = "optimization_tip"

@dataclass
class HardwareProfile:
    cpu_model: str
    gpu_model: Optional[str]
    ram_gb: int
    storage_type: str
    screen_resolution: Tuple[int, int]
    device_type: str
    os_version: str
    driver_versions: Dict[str, str] = field(default_factory=dict)
    power_profile: str = "balanced"
    thermal_design: str = "standard"

@dataclass
class PerformanceBenchmark:
    benchmark_id: str
    hardware_profile: HardwareProfile
    configuration_id: str
    metrics: Dict[str, float]  # response_time, memory_usage, cpu_usage, etc.
    test_scenarios: List[str]
    timestamp: datetime
    user_id: str
    verified: bool = False
    environment_conditions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserConfiguration:
    config_id: str
    user_id: str
    name: str
    description: str
    configuration_type: ConfigurationType
    hardware_profile: HardwareProfile
    settings: Dict[str, Any]
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    usage_count: int = 0
    success_rate: float = 0.0
    compatibility_score: float = 0.0
    performance_score: float = 0.0
    is_public: bool = True
    is_verified: bool = False
    expert_curated: bool = False

@dataclass
class ConfigurationReview:
    review_id: str
    config_id: str
    user_id: str
    rating: ReviewRating
    title: str
    content: str
    pros: List[str]
    cons: List[str]
    hardware_tested: HardwareProfile
    use_case: str
    performance_improvement: Optional[float]
    created_at: datetime
    helpful_votes: int = 0
    verified_purchase: bool = False

@dataclass
class TroubleshootingEntry:
    entry_id: str
    title: str
    problem_description: str
    solution: str
    affected_hardware: List[HardwareProfile]
    affected_configs: List[str]
    severity: str  # critical, major, minor
    status: str  # open, solved, investigating
    tags: List[str]
    user_id: str
    expert_verified: bool = False
    solution_rating: float = 0.0
    created_at: datetime
    updated_at: datetime

@dataclass
class FeatureRequest:
    request_id: str
    title: str
    description: str
    category: str
    priority: str
    user_id: str
    votes: int = 0
    status: str = "proposed"  # proposed, under_review, accepted, rejected, implemented
    implementation_complexity: str = "unknown"
    estimated_effort: Optional[int] = None
    target_release: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CommunityLearningNetwork:
    """Main community learning and knowledge sharing system"""
    
    def __init__(self):
        self.configurations: Dict[str, UserConfiguration] = {}
        self.reviews: Dict[str, List[ConfigurationReview]] = defaultdict(list)
        self.benchmarks: Dict[str, List[PerformanceBenchmark]] = defaultdict(list)
        self.troubleshooting: Dict[str, TroubleshootingEntry] = {}
        self.feature_requests: Dict[str, FeatureRequest] = {}
        
        # Community metrics and analytics
        self.user_reputation: Dict[str, float] = defaultdict(float)
        self.compatibility_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.performance_clusters: Dict[str, List[str]] = {}
        
        # Machine learning components
        self.config_recommender = ConfigurationRecommender()
        self.compatibility_predictor = CompatibilityPredictor()
        self.performance_estimator = PerformanceEstimator()
        
        # Threading for background tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.update_lock = threading.RLock()
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize with sample configurations and data"""
        # Sample hardware profiles
        gaming_hw = HardwareProfile(
            cpu_model="AMD Ryzen 7 7800X3D",
            gpu_model="NVIDIA RTX 4070 Ti",
            ram_gb=32,
            storage_type="NVMe SSD",
            screen_resolution=(2560, 1440),
            device_type="desktop",
            os_version="Windows 11 23H2"
        )
        
        productivity_hw = HardwareProfile(
            cpu_model="Intel Core i7-13700K",
            gpu_model="NVIDIA RTX 4060",
            ram_gb=16,
            storage_type="SATA SSD",
            screen_resolution=(1920, 1080),
            device_type="desktop",
            os_version="Windows 11 22H2"
        )
        
        # Sample configurations
        gaming_config = UserConfiguration(
            config_id="gaming_optimal_001",
            user_id="expert_gamer_123",
            name="High Performance Gaming Setup",
            description="Optimized configuration for competitive gaming with maximum FPS",
            configuration_type=ConfigurationType.GAMING,
            hardware_profile=gaming_hw,
            settings={
                "visual_effects": "performance",
                "caching_strategy": "aggressive",
                "prediction_enabled": True,
                "preload_level": "high",
                "thermal_throttling": False,
                "power_profile": "maximum_performance"
            },
            tags=["gaming", "high-fps", "competitive", "low-latency"],
            created_at=datetime.now() - timedelta(days=30),
            updated_at=datetime.now() - timedelta(days=5),
            usage_count=1247,
            success_rate=0.94,
            compatibility_score=0.89,
            performance_score=0.96,
            is_verified=True,
            expert_curated=True
        )
        
        productivity_config = UserConfiguration(
            config_id="productivity_balanced_001",
            user_id="office_expert_456",
            name="Balanced Productivity Configuration",
            description="Perfect balance of performance and battery life for office work",
            configuration_type=ConfigurationType.PRODUCTIVITY,
            hardware_profile=productivity_hw,
            settings={
                "visual_effects": "balanced",
                "caching_strategy": "intelligent",
                "prediction_enabled": True,
                "preload_level": "medium",
                "thermal_throttling": True,
                "power_profile": "balanced"
            },
            tags=["productivity", "office", "balanced", "battery-friendly"],
            created_at=datetime.now() - timedelta(days=45),
            updated_at=datetime.now() - timedelta(days=2),
            usage_count=856,
            success_rate=0.91,
            compatibility_score=0.95,
            performance_score=0.87,
            is_verified=True,
            expert_curated=True
        )
        
        self.configurations[gaming_config.config_id] = gaming_config
        self.configurations[productivity_config.config_id] = productivity_config
        
        # Sample reviews
        gaming_review = ConfigurationReview(
            review_id="review_001",
            config_id="gaming_optimal_001",
            user_id="pro_gamer_789",
            rating=ReviewRating.EXCELLENT,
            title="Incredible performance boost!",
            content="Saw immediate 15% FPS improvement and much smoother gameplay",
            pros=["Higher FPS", "Reduced input lag", "Stable performance"],
            cons=["Higher power consumption", "Fans run louder"],
            hardware_tested=gaming_hw,
            use_case="Competitive FPS gaming",
            performance_improvement=15.3,
            created_at=datetime.now() - timedelta(days=7),
            helpful_votes=23,
            verified_purchase=True
        )
        
        self.reviews["gaming_optimal_001"].append(gaming_review)
        
        logger.info("Initialized Community Learning Network with sample data")
    
    async def submit_configuration(self, config: UserConfiguration) -> bool:
        """Submit a new configuration to the community"""
        try:
            with self.update_lock:
                # Validate configuration
                if not await self._validate_configuration(config):
                    return False
                
                # Generate compatibility and performance scores
                config.compatibility_score = await self.compatibility_predictor.predict_compatibility(config)
                config.performance_score = await self.performance_estimator.estimate_performance(config)
                
                # Store configuration
                self.configurations[config.config_id] = config
                
                # Update user reputation
                self.user_reputation[config.user_id] += 2.0
                
                # Trigger background analysis
                asyncio.create_task(self._analyze_new_configuration(config))
                
                logger.info(f"Configuration {config.config_id} submitted successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error submitting configuration: {e}")
            return False
    
    async def _validate_configuration(self, config: UserConfiguration) -> bool:
        """Validate configuration before submission"""
        # Check required fields
        if not all([config.config_id, config.name, config.user_id]):
            return False
        
        # Check for duplicate config_id
        if config.config_id in self.configurations:
            return False
        
        # Validate hardware profile
        if not config.hardware_profile.cpu_model:
            return False
        
        # Validate settings format
        if not isinstance(config.settings, dict):
            return False
        
        return True
    
    async def _analyze_new_configuration(self, config: UserConfiguration):
        """Analyze new configuration in background"""
        try:
            # Find similar configurations
            similar_configs = await self.find_similar_configurations(
                config.hardware_profile, config.configuration_type
            )
            
            # Update compatibility matrix
            for similar_id, similarity in similar_configs:
                self.compatibility_matrix[config.config_id][similar_id] = similarity
                self.compatibility_matrix[similar_id][config.config_id] = similarity
            
            # Trigger clustering update
            await self._update_performance_clusters()
            
        except Exception as e:
            logger.error(f"Error analyzing configuration {config.config_id}: {e}")
    
    async def find_similar_configurations(self, hardware: HardwareProfile, 
                                        config_type: ConfigurationType) -> List[Tuple[str, float]]:
        """Find configurations similar to given hardware and type"""
        similar_configs = []
        
        for config_id, config in self.configurations.items():
            if config.configuration_type == config_type:
                similarity = self._calculate_hardware_similarity(hardware, config.hardware_profile)
                if similarity > 0.7:  # Threshold for similarity
                    similar_configs.append((config_id, similarity))
        
        # Sort by similarity
        similar_configs.sort(key=lambda x: x[1], reverse=True)
        return similar_configs[:10]  # Return top 10
    
    def _calculate_hardware_similarity(self, hw1: HardwareProfile, hw2: HardwareProfile) -> float:
        """Calculate similarity between two hardware profiles"""
        similarity_scores = []
        
        # Device type match (most important)
        if hw1.device_type == hw2.device_type:
            similarity_scores.append(1.0)
        else:
            similarity_scores.append(0.0)
        
        # RAM similarity
        ram_ratio = min(hw1.ram_gb, hw2.ram_gb) / max(hw1.ram_gb, hw2.ram_gb)
        similarity_scores.append(ram_ratio)
        
        # Storage type similarity
        storage_similarity = 1.0 if hw1.storage_type == hw2.storage_type else 0.5
        similarity_scores.append(storage_similarity)
        
        # Screen resolution similarity
        res1_pixels = hw1.screen_resolution[0] * hw1.screen_resolution[1]
        res2_pixels = hw2.screen_resolution[0] * hw2.screen_resolution[1]
        res_ratio = min(res1_pixels, res2_pixels) / max(res1_pixels, res2_pixels)
        similarity_scores.append(res_ratio)
        
        # CPU similarity (simplified brand matching)
        cpu_similarity = 0.8 if hw1.cpu_model.split()[0] == hw2.cpu_model.split()[0] else 0.3
        similarity_scores.append(cpu_similarity)
        
        # GPU similarity (if both have GPU)
        if hw1.gpu_model and hw2.gpu_model:
            gpu_similarity = 0.8 if hw1.gpu_model.split()[0] == hw2.gpu_model.split()[0] else 0.3
            similarity_scores.append(gpu_similarity)
        
        # Weighted average
        weights = [0.25, 0.15, 0.15, 0.15, 0.2, 0.1][:len(similarity_scores)]
        return np.average(similarity_scores, weights=weights)
    
    async def get_configuration_recommendations(self, user_hardware: HardwareProfile,
                                             config_type: ConfigurationType,
                                             user_id: str) -> List[Dict[str, Any]]:
        """Get personalized configuration recommendations"""
        try:
            # Find compatible configurations
            compatible_configs = await self.find_similar_configurations(user_hardware, config_type)
            
            recommendations = []
            for config_id, compatibility_score in compatible_configs:
                config = self.configurations[config_id]
                
                # Get reviews summary
                config_reviews = self.reviews.get(config_id, [])
                avg_rating = np.mean([r.rating.value for r in config_reviews]) if config_reviews else 3.0
                
                # Calculate recommendation score
                recommendation_score = (
                    compatibility_score * 0.4 +
                    config.performance_score * 0.3 +
                    config.success_rate * 0.2 +
                    (avg_rating / 5.0) * 0.1
                )
                
                recommendations.append({
                    "config_id": config_id,
                    "name": config.name,
                    "description": config.description,
                    "compatibility_score": compatibility_score,
                    "performance_score": config.performance_score,
                    "success_rate": config.success_rate,
                    "average_rating": avg_rating,
                    "recommendation_score": recommendation_score,
                    "usage_count": config.usage_count,
                    "tags": config.tags,
                    "is_verified": config.is_verified,
                    "expert_curated": config.expert_curated,
                    "estimated_improvement": await self._estimate_performance_improvement(
                        user_hardware, config
                    )
                })
            
            # Sort by recommendation score
            recommendations.sort(key=lambda x: x["recommendation_score"], reverse=True)
            
            return recommendations[:5]  # Return top 5 recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    async def _estimate_performance_improvement(self, user_hardware: HardwareProfile,
                                              config: UserConfiguration) -> float:
        """Estimate performance improvement for user's hardware"""
        try:
            # Get benchmarks for similar hardware
            similar_benchmarks = []
            
            for config_benchmarks in self.benchmarks.values():
                for benchmark in config_benchmarks:
                    hw_similarity = self._calculate_hardware_similarity(
                        user_hardware, benchmark.hardware_profile
                    )
                    if hw_similarity > 0.8:
                        similar_benchmarks.append(benchmark)
            
            if not similar_benchmarks:
                return 10.0  # Default estimate
            
            # Calculate average improvement
            improvements = []
            for benchmark in similar_benchmarks:
                if benchmark.configuration_id == config.config_id:
                    # Use reported performance metrics
                    baseline_score = 100.0  # Baseline
                    actual_score = benchmark.metrics.get("performance_score", 110.0)
                    improvement = ((actual_score - baseline_score) / baseline_score) * 100
                    improvements.append(improvement)
            
            return np.mean(improvements) if improvements else 10.0
            
        except Exception as e:
            logger.error(f"Error estimating performance improvement: {e}")
            return 0.0
    
    async def submit_review(self, review: ConfigurationReview) -> bool:
        """Submit a review for a configuration"""
        try:
            # Validate review
            if review.config_id not in self.configurations:
                return False
            
            # Store review
            self.reviews[review.config_id].append(review)
            
            # Update configuration ratings
            await self._update_configuration_ratings(review.config_id)
            
            # Update user reputation
            self.user_reputation[review.user_id] += 1.0
            
            logger.info(f"Review {review.review_id} submitted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting review: {e}")
            return False
    
    async def _update_configuration_ratings(self, config_id: str):
        """Update configuration ratings based on reviews"""
        try:
            config = self.configurations[config_id]
            config_reviews = self.reviews[config_id]
            
            if not config_reviews:
                return
            
            # Calculate weighted average rating
            total_weight = 0
            weighted_sum = 0
            
            for review in config_reviews:
                # Weight based on user reputation and helpful votes
                user_rep = self.user_reputation.get(review.user_id, 1.0)
                helpful_weight = min(review.helpful_votes / 10.0, 2.0)
                weight = user_rep * (1 + helpful_weight)
                
                weighted_sum += review.rating.value * weight
                total_weight += weight
            
            if total_weight > 0:
                avg_rating = weighted_sum / total_weight
                # Update success rate based on ratings
                config.success_rate = min(avg_rating / 5.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error updating ratings for {config_id}: {e}")
    
    async def submit_benchmark(self, benchmark: PerformanceBenchmark) -> bool:
        """Submit a performance benchmark"""
        try:
            # Validate benchmark
            if benchmark.configuration_id not in self.configurations:
                return False
            
            # Store benchmark
            self.benchmarks[benchmark.configuration_id].append(benchmark)
            
            # Update performance scores
            await self._update_performance_scores(benchmark.configuration_id)
            
            # Update user reputation
            self.user_reputation[benchmark.user_id] += 3.0
            
            logger.info(f"Benchmark {benchmark.benchmark_id} submitted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting benchmark: {e}")
            return False
    
    async def _update_performance_scores(self, config_id: str):
        """Update performance scores based on benchmarks"""
        try:
            config_benchmarks = self.benchmarks[config_id]
            
            if not config_benchmarks:
                return
            
            # Calculate average performance metrics
            response_times = []
            memory_usage = []
            cpu_usage = []
            
            for benchmark in config_benchmarks:
                metrics = benchmark.metrics
                if "response_time" in metrics:
                    response_times.append(metrics["response_time"])
                if "memory_usage" in metrics:
                    memory_usage.append(metrics["memory_usage"])
                if "cpu_usage" in metrics:
                    cpu_usage.append(metrics["cpu_usage"])
            
            # Update configuration performance score
            config = self.configurations[config_id]
            
            # Score based on performance (lower response time = higher score)
            if response_times:
                avg_response_time = np.mean(response_times)
                response_score = max(0, 1.0 - (avg_response_time / 1000.0))  # Normalize to 0-1
                config.performance_score = (config.performance_score + response_score) / 2
            
        except Exception as e:
            logger.error(f"Error updating performance scores: {e}")
    
    async def _update_performance_clusters(self):
        """Update performance clusters using machine learning"""
        try:
            if len(self.configurations) < 3:
                return
            
            # Extract features for clustering
            features = []
            config_ids = []
            
            for config_id, config in self.configurations.items():
                feature_vector = [
                    config.hardware_profile.ram_gb,
                    config.hardware_profile.screen_resolution[0],
                    config.hardware_profile.screen_resolution[1],
                    config.performance_score,
                    config.success_rate,
                    config.usage_count / 1000.0,  # Normalize
                    len(config.tags)
                ]
                features.append(feature_vector)
                config_ids.append(config_id)
            
            # Perform clustering
            features = np.array(features)
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            n_clusters = min(5, len(features))  # Max 5 clusters
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(features_scaled)
            
            # Update cluster assignments
            self.performance_clusters.clear()
            for i, cluster_id in enumerate(cluster_labels):
                cluster_name = f"cluster_{cluster_id}"
                if cluster_name not in self.performance_clusters:
                    self.performance_clusters[cluster_name] = []
                self.performance_clusters[cluster_name].append(config_ids[i])
            
            logger.info(f"Updated performance clusters: {len(self.performance_clusters)} clusters")
            
        except Exception as e:
            logger.error(f"Error updating performance clusters: {e}")
    
    async def get_hardware_compatibility_report(self, hardware: HardwareProfile) -> Dict[str, Any]:
        """Get comprehensive hardware compatibility report"""
        try:
            compatibility_report = {
                "hardware_profile": asdict(hardware),
                "compatible_configurations": [],
                "performance_estimates": {},
                "known_issues": [],
                "recommendations": [],
                "benchmark_data": []
            }
            
            # Find compatible configurations
            for config_type in ConfigurationType:
                compatible = await self.find_similar_configurations(hardware, config_type)
                compatibility_report["compatible_configurations"].extend([
                    {
                        "config_id": config_id,
                        "type": config_type.value,
                        "compatibility_score": score,
                        "name": self.configurations[config_id].name
                    }
                    for config_id, score in compatible[:3]  # Top 3 per type
                ])
            
            # Get performance estimates
            for config_id in [c["config_id"] for c in compatibility_report["compatible_configurations"]]:
                config = self.configurations[config_id]
                estimate = await self._estimate_performance_improvement(hardware, config)
                compatibility_report["performance_estimates"][config_id] = {
                    "estimated_improvement": estimate,
                    "confidence": min(config.compatibility_score, 1.0)
                }
            
            # Check for known issues
            known_issues = await self._check_hardware_issues(hardware)
            compatibility_report["known_issues"] = known_issues
            
            # Generate recommendations
            recommendations = await self._generate_hardware_recommendations(hardware)
            compatibility_report["recommendations"] = recommendations
            
            return compatibility_report
            
        except Exception as e:
            logger.error(f"Error generating compatibility report: {e}")
            return {}
    
    async def _check_hardware_issues(self, hardware: HardwareProfile) -> List[Dict[str, Any]]:
        """Check for known hardware issues"""
        issues = []
        
        # Check troubleshooting database
        for entry in self.troubleshooting.values():
            for affected_hw in entry.affected_hardware:
                similarity = self._calculate_hardware_similarity(hardware, affected_hw)
                if similarity > 0.8:
                    issues.append({
                        "issue_id": entry.entry_id,
                        "title": entry.title,
                        "severity": entry.severity,
                        "solution": entry.solution,
                        "status": entry.status,
                        "similarity": similarity
                    })
        
        return issues
    
    async def _generate_hardware_recommendations(self, hardware: HardwareProfile) -> List[Dict[str, Any]]:
        """Generate hardware optimization recommendations"""
        recommendations = []
        
        # Check RAM sufficiency
        if hardware.ram_gb < 16:
            recommendations.append({
                "type": "hardware_upgrade",
                "component": "RAM",
                "current": f"{hardware.ram_gb}GB",
                "recommended": "16GB or higher",
                "reason": "Insufficient RAM for optimal performance",
                "priority": "high",
                "estimated_improvement": "15-25%"
            })
        
        # Check storage type
        if hardware.storage_type.lower() not in ["nvme", "nvme ssd"]:
            recommendations.append({
                "type": "hardware_upgrade",
                "component": "Storage",
                "current": hardware.storage_type,
                "recommended": "NVMe SSD",
                "reason": "Faster storage improves loading times significantly",
                "priority": "medium",
                "estimated_improvement": "20-40%"
            })
        
        # Check resolution vs performance balance
        pixels = hardware.screen_resolution[0] * hardware.screen_resolution[1]
        if pixels > 2073600 and not hardware.gpu_model:  # 1440p without dedicated GPU
            recommendations.append({
                "type": "configuration",
                "component": "Display Settings",
                "recommendation": "Consider lower resolution or dedicated GPU",
                "reason": "High resolution without GPU acceleration may impact performance",
                "priority": "medium",
                "estimated_improvement": "10-20%"
            })
        
        return recommendations
    
    async def submit_feature_request(self, request: FeatureRequest) -> bool:
        """Submit a feature request"""
        try:
            self.feature_requests[request.request_id] = request
            self.user_reputation[request.user_id] += 0.5
            
            logger.info(f"Feature request {request.request_id} submitted")
            return True
            
        except Exception as e:
            logger.error(f"Error submitting feature request: {e}")
            return False
    
    async def vote_feature_request(self, request_id: str, user_id: str, vote: int) -> bool:
        """Vote on a feature request"""
        try:
            if request_id not in self.feature_requests:
                return False
            
            # Update votes (simplified - in real system would track individual votes)
            self.feature_requests[request_id].votes += vote
            self.user_reputation[user_id] += 0.1
            
            return True
            
        except Exception as e:
            logger.error(f"Error voting on feature request: {e}")
            return False
    
    async def get_community_stats(self) -> Dict[str, Any]:
        """Get community statistics"""
        try:
            total_configs = len(self.configurations)
            total_reviews = sum(len(reviews) for reviews in self.reviews.values())
            total_benchmarks = sum(len(benchmarks) for benchmarks in self.benchmarks.values())
            
            # Configuration type distribution
            type_distribution = Counter(config.configuration_type.value for config in self.configurations.values())
            
            # Top contributors
            top_contributors = sorted(
                self.user_reputation.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Average ratings by type
            type_ratings = {}
            for config_type in ConfigurationType:
                type_configs = [c for c in self.configurations.values() if c.configuration_type == config_type]
                if type_configs:
                    avg_success_rate = np.mean([c.success_rate for c in type_configs])
                    type_ratings[config_type.value] = avg_success_rate
            
            return {
                "total_configurations": total_configs,
                "total_reviews": total_reviews,
                "total_benchmarks": total_benchmarks,
                "total_troubleshooting_entries": len(self.troubleshooting),
                "total_feature_requests": len(self.feature_requests),
                "configuration_type_distribution": dict(type_distribution),
                "top_contributors": [{"user_id": uid, "reputation": rep} for uid, rep in top_contributors],
                "average_ratings_by_type": type_ratings,
                "total_active_users": len(self.user_reputation),
                "performance_clusters": len(self.performance_clusters)
            }
            
        except Exception as e:
            logger.error(f"Error getting community stats: {e}")
            return {}
    
    async def get_marketplace_listings(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get marketplace listings of configurations"""
        try:
            listings = []
            
            for config in self.configurations.values():
                if not config.is_public:
                    continue
                
                if category and config.configuration_type.value != category:
                    continue
                
                # Get reviews summary
                config_reviews = self.reviews.get(config.config_id, [])
                avg_rating = np.mean([r.rating.value for r in config_reviews]) if config_reviews else 0
                review_count = len(config_reviews)
                
                # Get latest benchmarks
                config_benchmarks = self.benchmarks.get(config.config_id, [])
                recent_benchmarks = sorted(
                    config_benchmarks,
                    key=lambda x: x.timestamp,
                    reverse=True
                )[:5]
                
                listing = {
                    "config_id": config.config_id,
                    "name": config.name,
                    "description": config.description,
                    "category": config.configuration_type.value,
                    "tags": config.tags,
                    "usage_count": config.usage_count,
                    "success_rate": config.success_rate,
                    "performance_score": config.performance_score,
                    "compatibility_score": config.compatibility_score,
                    "average_rating": avg_rating,
                    "review_count": review_count,
                    "is_verified": config.is_verified,
                    "expert_curated": config.expert_curated,
                    "created_at": config.created_at.isoformat(),
                    "updated_at": config.updated_at.isoformat(),
                    "hardware_requirements": {
                        "min_ram_gb": config.hardware_profile.ram_gb,
                        "storage_type": config.hardware_profile.storage_type,
                        "device_type": config.hardware_profile.device_type
                    },
                    "recent_benchmark_count": len(recent_benchmarks),
                    "contributor_reputation": self.user_reputation.get(config.user_id, 0)
                }
                
                listings.append(listing)
            
            # Sort by popularity and rating
            listings.sort(
                key=lambda x: (x["usage_count"] * 0.4 + 
                             x["average_rating"] * 0.3 + 
                             x["performance_score"] * 0.3),
                reverse=True
            )
            
            return listings
            
        except Exception as e:
            logger.error(f"Error getting marketplace listings: {e}")
            return []

class ConfigurationRecommender:
    """ML-based configuration recommender system"""
    
    def __init__(self):
        self.similarity_threshold = 0.7
        
    async def get_personalized_recommendations(self, user_profile: Dict[str, Any],
                                             available_configs: List[UserConfiguration]) -> List[Tuple[str, float]]:
        """Get personalized recommendations using collaborative filtering"""
        try:
            recommendations = []
            
            user_hardware = user_profile.get("hardware_profile")
            user_preferences = user_profile.get("preferences", {})
            
            for config in available_configs:
                score = await self._calculate_recommendation_score(
                    user_hardware, user_preferences, config
                )
                if score > 0.5:
                    recommendations.append((config.config_id, score))
            
            return sorted(recommendations, key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting personalized recommendations: {e}")
            return []
    
    async def _calculate_recommendation_score(self, user_hardware: HardwareProfile,
                                           user_preferences: Dict[str, Any],
                                           config: UserConfiguration) -> float:
        """Calculate recommendation score for a configuration"""
        score_components = []
        
        # Hardware compatibility score
        if user_hardware:
            hw_similarity = self._calculate_hardware_similarity(user_hardware, config.hardware_profile)
            score_components.append(hw_similarity * 0.4)
        
        # Performance score
        score_components.append(config.performance_score * 0.3)
        
        # Success rate score
        score_components.append(config.success_rate * 0.2)
        
        # Popularity score
        popularity = min(config.usage_count / 1000.0, 1.0)
        score_components.append(popularity * 0.1)
        
        return np.mean(score_components)
    
    def _calculate_hardware_similarity(self, hw1: HardwareProfile, hw2: HardwareProfile) -> float:
        """Calculate hardware similarity (same as in main class)"""
        # Implementation would be same as CommunityLearningNetwork method
        return 0.8  # Simplified for brevity

class CompatibilityPredictor:
    """Predict configuration compatibility with hardware"""
    
    async def predict_compatibility(self, config: UserConfiguration) -> float:
        """Predict compatibility score for configuration"""
        try:
            # Simplified compatibility prediction
            base_score = 0.8
            
            # Adjust based on hardware requirements
            hardware = config.hardware_profile
            
            if hardware.ram_gb >= 16:
                base_score += 0.1
            if hardware.storage_type.lower() in ["nvme", "ssd"]:
                base_score += 0.05
            if hardware.gpu_model:
                base_score += 0.05
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error predicting compatibility: {e}")
            return 0.5

class PerformanceEstimator:
    """Estimate performance for configurations"""
    
    async def estimate_performance(self, config: UserConfiguration) -> float:
        """Estimate performance score for configuration"""
        try:
            # Simplified performance estimation
            base_score = 0.7
            
            # Adjust based on configuration settings
            settings = config.settings
            
            if settings.get("caching_strategy") == "aggressive":
                base_score += 0.1
            if settings.get("prediction_enabled"):
                base_score += 0.05
            if settings.get("preload_level") == "high":
                base_score += 0.05
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error estimating performance: {e}")
            return 0.5

# Usage example
async def main():
    """Example usage of Community Learning Network"""
    network = CommunityLearningNetwork()
    
    # Test hardware profile
    test_hardware = HardwareProfile(
        cpu_model="Intel Core i5-12600K",
        gpu_model="NVIDIA RTX 3070",
        ram_gb=16,
        storage_type="NVMe SSD",
        screen_resolution=(1920, 1080),
        device_type="desktop",
        os_version="Windows 11"
    )
    
    print("Getting configuration recommendations...")
    recommendations = await network.get_configuration_recommendations(
        test_hardware, ConfigurationType.GAMING, "test_user"
    )
    
    print(f"Found {len(recommendations)} recommendations")
    for rec in recommendations:
        print(f"- {rec['name']}: {rec['recommendation_score']:.2f}")
    
    print("\nGetting hardware compatibility report...")
    compatibility_report = await network.get_hardware_compatibility_report(test_hardware)
    print(f"Compatible configurations: {len(compatibility_report.get('compatible_configurations', []))}")
    
    print("\nCommunity stats:")
    stats = await network.get_community_stats()
    print(f"Total configurations: {stats.get('total_configurations', 0)}")
    print(f"Total reviews: {stats.get('total_reviews', 0)}")

if __name__ == "__main__":
    asyncio.run(main())