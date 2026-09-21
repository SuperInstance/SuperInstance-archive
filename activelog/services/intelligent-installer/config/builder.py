"""
Smart Configuration Builder
ML-powered configuration generation and optimization system
"""

import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pickle
import hashlib
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from api.models import (
    HardwareProfile, AdaptiveConfiguration, InterfaceType, 
    ComputeDistribution, OptimizationGoal, SystemTier,
    PerformancePrediction
)
from adaptive.interface_generator import InterfaceGenerator, ComponentComplexity
from adaptive.compute_distributor import ComputeDistributor, ExecutionContext

class ConfigurationClassifier:
    """ML-based configuration classification and recommendation system"""
    
    def __init__(self):
        self.hardware_clusterer = None
        self.performance_predictor = None
        self.configuration_recommender = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
    def extract_hardware_features(self, hardware_profile: HardwareProfile) -> np.ndarray:
        """Extract numerical features from hardware profile for ML"""
        
        features = []
        
        # CPU features
        features.extend([
            hardware_profile.cpu.cores,
            hardware_profile.cpu.threads,
            hardware_profile.cpu.base_frequency_ghz,
            hardware_profile.cpu.max_frequency_ghz or hardware_profile.cpu.base_frequency_ghz,
            hardware_profile.cpu.tdp_watts or 65,  # Default TDP
        ])
        
        # Memory features
        features.extend([
            hardware_profile.memory.total_gb,
            hardware_profile.memory.available_gb,
            hardware_profile.memory.speed_mhz or 2400,  # Default speed
            hardware_profile.memory.bandwidth_gb_s or 20,  # Estimated bandwidth
        ])
        
        # GPU features (0 if no GPU)
        if hardware_profile.gpu:
            features.extend([
                1.0,  # GPU present
                hardware_profile.gpu.memory_gb or 2.0,
                hardware_profile.gpu.cuda_cores or 1000,  # Estimated
                hardware_profile.gpu.base_clock_mhz or 1000,  # Estimated
            ])
        else:
            features.extend([0.0, 0.0, 0.0, 0.0])
        
        # Storage features
        features.extend([
            hardware_profile.storage.total_capacity_gb,
            hardware_profile.storage.available_capacity_gb,
            1.0 if hardware_profile.storage.primary_type == 'SSD' else 0.0,
            hardware_profile.storage.read_speed_mb_s or 100,  # Estimated
            hardware_profile.storage.write_speed_mb_s or 80,  # Estimated
        ])
        
        # Network features
        features.extend([
            hardware_profile.network.max_bandwidth_mbps,
            hardware_profile.network.latency_ms or 50,  # Estimated
            hardware_profile.network.stability_score or 0.8,  # Estimated
        ])
        
        # Display features
        if hardware_profile.display:
            features.extend([
                hardware_profile.display.total_pixels,
                hardware_profile.display.primary_refresh_rate_hz,
                1.0 if hardware_profile.display.hdr_support else 0.0,
            ])
        else:
            features.extend([1920*1080, 60, 0.0])  # Default values
        
        # Power features
        if hardware_profile.power:
            features.extend([
                1.0 if hardware_profile.power.battery_present else 0.0,
                hardware_profile.power.battery_capacity_wh or 50,  # Estimated
                hardware_profile.power.battery_health_percent or 100,
                hardware_profile.power.current_power_draw_watts or 50,  # Estimated
            ])
        else:
            features.extend([0.0, 0.0, 100.0, 50.0])
        
        # System tier encoding
        tier_encoding = {
            SystemTier.EMBEDDED: 1,
            SystemTier.BASIC: 2,
            SystemTier.STANDARD: 3,
            SystemTier.HIGH_END: 4,
            SystemTier.ENTERPRISE: 5,
            SystemTier.SPECIALIZED: 6
        }
        features.append(tier_encoding.get(hardware_profile.system_tier, 3))
        
        return np.array(features)
    
    def train_models(self, training_data: List[Dict[str, Any]]):
        """Train ML models on historical configuration data"""
        
        if not training_data:
            # Generate synthetic training data for initial model
            training_data = self._generate_synthetic_training_data()
        
        # Extract features and targets
        X = []
        y_performance = []
        y_satisfaction = []
        
        for data_point in training_data:
            hardware_features = self.extract_hardware_features(data_point['hardware_profile'])
            X.append(hardware_features)
            y_performance.append(data_point.get('performance_score', 75.0))
            y_satisfaction.append(data_point.get('user_satisfaction', 0.8))
        
        X = np.array(X)
        y_performance = np.array(y_performance)
        y_satisfaction = np.array(y_satisfaction)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train hardware clustering model
        self.hardware_clusterer = KMeans(n_clusters=min(8, len(X)), random_state=42)
        hardware_clusters = self.hardware_clusterer.fit_predict(X_scaled)
        
        # Train performance prediction model
        self.performance_predictor = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Add cluster information as features
        X_with_clusters = np.column_stack([X_scaled, hardware_clusters])
        
        # Split data for validation
        if len(X) > 10:
            X_train, X_test, y_train, y_test = train_test_split(
                X_with_clusters, y_performance, test_size=0.2, random_state=42
            )
            
            self.performance_predictor.fit(X_train, y_train)
            
            # Evaluate model
            y_pred = self.performance_predictor.predict(X_test)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            print(f"Performance Predictor - MSE: {mse:.2f}, R²: {r2:.2f}")
        else:
            self.performance_predictor.fit(X_with_clusters, y_performance)
        
        # Store feature names for interpretability
        self.feature_names = [
            'cpu_cores', 'cpu_threads', 'cpu_base_freq', 'cpu_max_freq', 'cpu_tdp',
            'memory_total', 'memory_available', 'memory_speed', 'memory_bandwidth',
            'gpu_present', 'gpu_memory', 'gpu_cores', 'gpu_clock',
            'storage_total', 'storage_available', 'storage_is_ssd', 'storage_read_speed', 'storage_write_speed',
            'network_bandwidth', 'network_latency', 'network_stability',
            'display_pixels', 'display_refresh', 'display_hdr',
            'battery_present', 'battery_capacity', 'battery_health', 'power_draw',
            'system_tier', 'hardware_cluster'
        ]
        
        self.is_trained = True
    
    def predict_performance(self, hardware_profile: HardwareProfile,
                          configuration: AdaptiveConfiguration) -> PerformancePrediction:
        """Predict performance for a given hardware/configuration combination"""
        
        if not self.is_trained:
            # Return default prediction if not trained
            return PerformancePrediction(
                config_id=configuration.config_id,
                predicted_metrics={'overall_score': 75.0},
                confidence_intervals={'overall_score': [70.0, 80.0]},
                bottlenecks=['unknown'],
                recommendations=['Train ML models with historical data for better predictions']
            )
        
        # Extract and scale features
        hardware_features = self.extract_hardware_features(hardware_profile)
        hardware_features_scaled = self.scaler.transform([hardware_features])
        
        # Get hardware cluster
        hardware_cluster = self.hardware_clusterer.predict(hardware_features_scaled)[0]
        
        # Add cluster to features
        features_with_cluster = np.column_stack([hardware_features_scaled, [hardware_cluster]])
        
        # Predict performance
        predicted_score = self.performance_predictor.predict(features_with_cluster)[0]
        
        # Calculate confidence interval (simplified)
        confidence_range = 10.0  # ±10 points
        confidence_interval = [
            max(0, predicted_score - confidence_range),
            min(100, predicted_score + confidence_range)
        ]
        
        # Identify potential bottlenecks
        bottlenecks = self._identify_bottlenecks(hardware_profile, configuration)
        
        # Generate recommendations
        recommendations = self._generate_performance_recommendations(
            hardware_profile, configuration, predicted_score, bottlenecks
        )
        
        return PerformancePrediction(
            config_id=configuration.config_id,
            predicted_metrics={
                'overall_score': predicted_score,
                'cpu_utilization': min(100, predicted_score * 0.8),
                'memory_utilization': min(100, predicted_score * 0.7),
                'responsiveness': max(0, predicted_score - 20),
            },
            confidence_intervals={
                'overall_score': confidence_interval,
            },
            bottlenecks=bottlenecks,
            recommendations=recommendations
        )
    
    def _generate_synthetic_training_data(self) -> List[Dict[str, Any]]:
        """Generate synthetic training data for initial model training"""
        
        synthetic_data = []
        
        # Generate diverse hardware profiles
        for i in range(100):
            # Random hardware specifications
            cpu_cores = np.random.choice([2, 4, 6, 8, 12, 16])
            memory_gb = np.random.choice([4, 8, 16, 32, 64])
            gpu_present = np.random.choice([True, False], p=[0.6, 0.4])
            storage_type = np.random.choice(['SSD', 'HDD'], p=[0.7, 0.3])
            
            # Determine system tier based on specs
            tier_score = (cpu_cores / 16) + (memory_gb / 64) + (0.3 if gpu_present else 0)
            if tier_score > 0.8:
                system_tier = SystemTier.HIGH_END
            elif tier_score > 0.5:
                system_tier = SystemTier.STANDARD
            else:
                system_tier = SystemTier.BASIC
            
            # Create synthetic hardware profile
            from api.models import CPUInfo, MemoryInfo, GPUInfo, StorageInfo, NetworkInfo
            
            cpu_info = CPUInfo(
                name=f"CPU_{i}",
                manufacturer="Synthetic",
                architecture="x86_64",
                cores=cpu_cores,
                threads=cpu_cores * 2,
                base_frequency_ghz=2.5 + np.random.uniform(-0.5, 1.0),
                tdp_watts=65 + cpu_cores * 5
            )
            
            memory_info = MemoryInfo(
                total_gb=memory_gb,
                available_gb=memory_gb * 0.8,
                used_gb=memory_gb * 0.2,
                memory_type="DDR4",
                speed_mhz=2400 + np.random.randint(0, 800)
            )
            
            gpu_info = None
            if gpu_present:
                gpu_info = GPUInfo(
                    name=f"GPU_{i}",
                    manufacturer="Synthetic",
                    memory_gb=np.random.choice([4, 6, 8, 12]),
                    cuda_cores=np.random.randint(1000, 5000)
                )
            
            storage_info = StorageInfo(
                drives=[],
                total_capacity_gb=500 + np.random.randint(0, 1500),
                available_capacity_gb=300 + np.random.randint(0, 700),
                primary_type=storage_type,
                read_speed_mb_s=500 if storage_type == 'SSD' else 100,
                write_speed_mb_s=400 if storage_type == 'SSD' else 80
            )
            
            network_info = NetworkInfo(
                interfaces=[],
                max_bandwidth_mbps=np.random.choice([10, 50, 100, 1000]),
                latency_ms=np.random.uniform(10, 100),
                stability_score=np.random.uniform(0.6, 0.95)
            )
            
            hardware_profile = HardwareProfile(
                profile_id=f"synthetic_{i}",
                system_tier=system_tier,
                cpu=cpu_info,
                memory=memory_info,
                gpu=gpu_info,
                storage=storage_info,
                network=network_info
            )
            
            # Calculate synthetic performance score based on hardware
            performance_score = self._calculate_synthetic_performance(hardware_profile)
            user_satisfaction = min(1.0, performance_score / 100.0 + np.random.uniform(-0.2, 0.2))
            
            synthetic_data.append({
                'hardware_profile': hardware_profile,
                'performance_score': performance_score,
                'user_satisfaction': max(0.0, user_satisfaction)
            })
        
        return synthetic_data
    
    def _calculate_synthetic_performance(self, hardware_profile: HardwareProfile) -> float:
        """Calculate synthetic performance score for training data"""
        
        score = 0.0
        
        # CPU contribution
        cpu_score = (hardware_profile.cpu.cores * hardware_profile.cpu.base_frequency_ghz) / 20
        score += min(30, cpu_score)
        
        # Memory contribution
        memory_score = hardware_profile.memory.total_gb / 2
        score += min(25, memory_score)
        
        # GPU contribution
        if hardware_profile.gpu:
            gpu_score = (hardware_profile.gpu.memory_gb or 4) * 3
            score += min(20, gpu_score)
        
        # Storage contribution
        if hardware_profile.storage.primary_type == 'SSD':
            score += 15
        else:
            score += 5
        
        # Network contribution
        network_score = hardware_profile.network.max_bandwidth_mbps / 100
        score += min(10, network_score)
        
        # Add some randomness
        score += np.random.uniform(-10, 10)
        
        return max(0, min(100, score))
    
    def _identify_bottlenecks(self, hardware_profile: HardwareProfile,
                            configuration: AdaptiveConfiguration) -> List[str]:
        """Identify potential performance bottlenecks"""
        
        bottlenecks = []
        
        # CPU bottleneck
        if (hardware_profile.cpu.cores < 4 and 
            configuration.processing_threads > hardware_profile.cpu.cores):
            bottlenecks.append('insufficient_cpu_cores')
        
        # Memory bottleneck
        memory_usage_estimate = configuration.memory_allocation_mb / 1024
        if memory_usage_estimate > hardware_profile.memory.available_gb * 0.8:
            bottlenecks.append('insufficient_memory')
        
        # GPU bottleneck
        if (configuration.ml_acceleration and 
            (not hardware_profile.gpu or not hardware_profile.gpu.memory_gb or 
             hardware_profile.gpu.memory_gb < 4)):
            bottlenecks.append('insufficient_gpu_memory')
        
        # Storage bottleneck
        if (hardware_profile.storage.primary_type == 'HDD' and 
            configuration.cache_size_mb > 500):
            bottlenecks.append('slow_storage')
        
        # Network bottleneck
        if (configuration.cloud_fallback and 
            hardware_profile.network.max_bandwidth_mbps < 50):
            bottlenecks.append('limited_bandwidth')
        
        return bottlenecks if bottlenecks else ['none_detected']
    
    def _generate_performance_recommendations(self, 
                                            hardware_profile: HardwareProfile,
                                            configuration: AdaptiveConfiguration,
                                            predicted_score: float,
                                            bottlenecks: List[str]) -> List[str]:
        """Generate performance improvement recommendations"""
        
        recommendations = []
        
        if predicted_score < 60:
            recommendations.append("Consider upgrading hardware for better performance")
        
        if 'insufficient_cpu_cores' in bottlenecks:
            recommendations.append("Reduce processing threads or upgrade CPU")
        
        if 'insufficient_memory' in bottlenecks:
            recommendations.append("Reduce memory allocation or add more RAM")
        
        if 'insufficient_gpu_memory' in bottlenecks:
            recommendations.append("Disable ML acceleration or upgrade GPU")
        
        if 'slow_storage' in bottlenecks:
            recommendations.append("Reduce cache size or upgrade to SSD")
        
        if 'limited_bandwidth' in bottlenecks:
            recommendations.append("Disable cloud fallback or upgrade internet connection")
        
        # General optimization recommendations
        if hardware_profile.power and hardware_profile.power.battery_present:
            recommendations.append("Enable power management for battery optimization")
        
        if hardware_profile.system_tier == SystemTier.BASIC:
            recommendations.append("Use minimal interface for better performance")
        
        return recommendations if recommendations else ["Configuration appears well-optimized"]

class SmartConfigurationBuilder:
    """Main configuration builder with ML-powered optimization"""
    
    def __init__(self):
        self.interface_generator = InterfaceGenerator()
        self.compute_distributor = ComputeDistributor()
        self.classifier = ConfigurationClassifier()
        self.configuration_history = []
        self.optimization_cache = {}
        
    async def build_configuration(self, 
                                hardware_profile: HardwareProfile,
                                use_case: str,
                                user_preferences: Optional[Dict] = None,
                                optimization_goals: Optional[List[OptimizationGoal]] = None) -> AdaptiveConfiguration:
        """Build optimal configuration for given requirements"""
        
        # Generate unique configuration ID
        config_id = self._generate_config_id(hardware_profile, use_case, user_preferences)
        
        # Check cache first
        cached_config = self._get_cached_configuration(config_id)
        if cached_config:
            return cached_config
        
        # Determine optimal interface type
        interface_config = self.interface_generator.generate_interface_config(
            hardware_profile, user_preferences
        )
        interface_type = InterfaceType(interface_config['interface_type'])
        
        # Determine optimal compute distribution
        task_requirements = self._extract_task_requirements(use_case, user_preferences)
        compute_distribution = await self.compute_distributor.determine_optimal_distribution(
            hardware_profile, task_requirements, user_preferences
        )
        
        # Build base configuration
        base_config = self._build_base_configuration(
            config_id, interface_type, compute_distribution, 
            hardware_profile, use_case, optimization_goals or []
        )
        
        # Apply ML-based optimizations
        optimized_config = await self._apply_ml_optimizations(
            base_config, hardware_profile, use_case, user_preferences
        )
        
        # Generate performance predictions
        performance_prediction = self.classifier.predict_performance(
            hardware_profile, optimized_config
        )
        
        # Store prediction in configuration
        optimized_config.predicted_performance = performance_prediction.predicted_metrics
        optimized_config.confidence_score = self._calculate_confidence_score(performance_prediction)
        
        # Cache the configuration
        self._cache_configuration(optimized_config)
        
        return optimized_config
    
    async def optimize_configuration(self,
                                   configuration: AdaptiveConfiguration,
                                   hardware_profile: HardwareProfile,
                                   performance_feedback: Dict[str, float],
                                   user_feedback: Optional[Dict] = None) -> AdaptiveConfiguration:
        """Optimize existing configuration based on feedback"""
        
        # Analyze performance gaps
        performance_gaps = self._analyze_performance_gaps(
            configuration.predicted_performance, performance_feedback
        )
        
        # Generate optimization recommendations
        optimizations = await self._generate_optimizations(
            configuration, hardware_profile, performance_gaps, user_feedback
        )
        
        # Apply optimizations
        optimized_config = self._apply_optimizations(configuration, optimizations)
        
        # Update predictions
        new_prediction = self.classifier.predict_performance(
            hardware_profile, optimized_config
        )
        optimized_config.predicted_performance = new_prediction.predicted_metrics
        optimized_config.confidence_score = self._calculate_confidence_score(new_prediction)
        
        return optimized_config
    
    def train_from_history(self):
        """Train ML models from configuration history"""
        
        if len(self.configuration_history) < 10:
            print("Insufficient historical data for training. Using synthetic data.")
        
        self.classifier.train_models(self.configuration_history)
    
    def _generate_config_id(self, hardware_profile: HardwareProfile, 
                          use_case: str, user_preferences: Optional[Dict]) -> str:
        """Generate unique configuration identifier"""
        
        content = f"{hardware_profile.profile_id}_{use_case}"
        if user_preferences:
            content += f"_{hash(json.dumps(user_preferences, sort_keys=True))}"
        
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _get_cached_configuration(self, config_id: str) -> Optional[AdaptiveConfiguration]:
        """Get cached configuration if available and valid"""
        
        if config_id in self.optimization_cache:
            cached_entry = self.optimization_cache[config_id]
            # Check if cache is still valid (e.g., less than 1 hour old)
            cache_age = datetime.now() - cached_entry['timestamp']
            if cache_age.total_seconds() < 3600:  # 1 hour
                return cached_entry['configuration']
        
        return None
    
    def _extract_task_requirements(self, use_case: str, 
                                 user_preferences: Optional[Dict]) -> Dict[str, Any]:
        """Extract task requirements from use case and preferences"""
        
        # Default requirements
        requirements = {
            'estimated_runtime_seconds': 5.0,
            'cpu_intensive': False,
            'memory_requirement_gb': 2.0,
            'gpu_required': False,
            'parallel_tasks': 1,
            'network_bandwidth_mbps': 10.0,
            'storage_requirement_gb': 1.0
        }
        
        # Adjust based on use case
        use_case_lower = use_case.lower()
        
        if 'gaming' in use_case_lower or 'game' in use_case_lower:
            requirements.update({
                'cpu_intensive': True,
                'gpu_required': True,
                'memory_requirement_gb': 8.0,
                'estimated_runtime_seconds': 3600  # 1 hour session
            })
        elif 'ml' in use_case_lower or 'ai' in use_case_lower or 'machine learning' in use_case_lower:
            requirements.update({
                'cpu_intensive': True,
                'gpu_required': True,
                'memory_requirement_gb': 16.0,
                'estimated_runtime_seconds': 600,  # 10 minutes
                'parallel_tasks': 4
            })
        elif 'video' in use_case_lower or 'streaming' in use_case_lower:
            requirements.update({
                'cpu_intensive': True,
                'memory_requirement_gb': 6.0,
                'network_bandwidth_mbps': 50.0,
                'gpu_required': True
            })
        elif 'development' in use_case_lower or 'coding' in use_case_lower:
            requirements.update({
                'memory_requirement_gb': 8.0,
                'storage_requirement_gb': 5.0,
                'parallel_tasks': 2
            })
        elif 'office' in use_case_lower or 'productivity' in use_case_lower:
            requirements.update({
                'memory_requirement_gb': 4.0,
                'cpu_intensive': False
            })
        
        # Apply user preference overrides
        if user_preferences:
            if 'performance_priority' in user_preferences and user_preferences['performance_priority']:
                requirements['memory_requirement_gb'] *= 1.5
                requirements['parallel_tasks'] *= 2
            
            if 'battery_conservation' in user_preferences and user_preferences['battery_conservation']:
                requirements['cpu_intensive'] = False
                requirements['gpu_required'] = False
        
        return requirements
    
    def _build_base_configuration(self, 
                                config_id: str,
                                interface_type: InterfaceType,
                                compute_distribution: ComputeDistribution,
                                hardware_profile: HardwareProfile,
                                use_case: str,
                                optimization_goals: List[OptimizationGoal]) -> AdaptiveConfiguration:
        """Build base configuration before ML optimization"""
        
        # Determine UI complexity based on hardware and interface type
        ui_complexity = self._determine_ui_complexity(hardware_profile, interface_type)
        animation_level = self._determine_animation_level(hardware_profile, interface_type)
        asset_quality = self._determine_asset_quality(hardware_profile, interface_type)
        
        # Calculate resource allocations
        max_concurrent_tasks = min(8, max(1, hardware_profile.cpu.threads // 2))
        memory_allocation_mb = min(
            int(hardware_profile.memory.available_gb * 1024 * 0.6),  # 60% of available
            8192  # Max 8GB
        )
        cache_size_mb = min(
            int(hardware_profile.memory.available_gb * 1024 * 0.1),  # 10% of available
            1024  # Max 1GB
        )
        processing_threads = min(hardware_profile.cpu.threads, max_concurrent_tasks * 2)
        
        # Determine target utilizations
        cpu_target = 70.0 if OptimizationGoal.PERFORMANCE in optimization_goals else 50.0
        memory_target = 80.0 if OptimizationGoal.PERFORMANCE in optimization_goals else 60.0
        
        # Power profile
        power_profile = "performance"
        if OptimizationGoal.BATTERY_LIFE in optimization_goals:
            power_profile = "efficiency"
        elif OptimizationGoal.EFFICIENCY in optimization_goals:
            power_profile = "balanced"
        
        # ML acceleration
        ml_acceleration = (hardware_profile.gpu is not None and 
                          hardware_profile.gpu.memory_gb and 
                          hardware_profile.gpu.memory_gb >= 4)
        
        # Cloud fallback
        cloud_fallback = (hardware_profile.network.max_bandwidth_mbps >= 25 and
                         OptimizationGoal.PERFORMANCE in optimization_goals)
        
        # Offline mode
        offline_mode = (hardware_profile.network.max_bandwidth_mbps < 10 or
                       OptimizationGoal.COST_OPTIMIZATION in optimization_goals)
        
        return AdaptiveConfiguration(
            config_id=config_id,
            interface_type=interface_type,
            compute_distribution=compute_distribution,
            ui_complexity=ui_complexity,
            animation_level=animation_level,
            asset_quality=asset_quality,
            responsive_breakpoints=[576, 768, 992, 1200],
            max_concurrent_tasks=max_concurrent_tasks,
            memory_allocation_mb=memory_allocation_mb,
            cache_size_mb=cache_size_mb,
            processing_threads=processing_threads,
            cpu_utilization_target=cpu_target,
            memory_utilization_target=memory_target,
            power_profile=power_profile,
            thermal_management=True,
            optimization_goals=optimization_goals,
            ml_acceleration=ml_acceleration,
            cloud_fallback=cloud_fallback,
            offline_mode=offline_mode,
            predicted_performance={},
            estimated_resource_usage={},
            confidence_score=0.5
        )
    
    async def _apply_ml_optimizations(self,
                                    base_config: AdaptiveConfiguration,
                                    hardware_profile: HardwareProfile,
                                    use_case: str,
                                    user_preferences: Optional[Dict]) -> AdaptiveConfiguration:
        """Apply ML-based optimizations to base configuration"""
        
        # If ML model is not trained, return base configuration
        if not self.classifier.is_trained:
            return base_config
        
        # Generate prediction for base configuration
        base_prediction = self.classifier.predict_performance(hardware_profile, base_config)
        
        # If prediction is already good, minor optimizations only
        if base_prediction.predicted_metrics.get('overall_score', 0) > 80:
            return self._apply_minor_optimizations(base_config, base_prediction)
        
        # Try different optimization strategies
        optimization_candidates = []
        
        # Strategy 1: Reduce resource usage if bottlenecked
        if 'insufficient_memory' in base_prediction.bottlenecks:
            candidate = self._reduce_memory_usage(base_config)
            optimization_candidates.append(candidate)
        
        # Strategy 2: Adjust parallelism
        if 'insufficient_cpu_cores' in base_prediction.bottlenecks:
            candidate = self._reduce_parallelism(base_config)
            optimization_candidates.append(candidate)
        
        # Strategy 3: Disable expensive features
        if base_prediction.predicted_metrics.get('overall_score', 0) < 60:
            candidate = self._disable_expensive_features(base_config)
            optimization_candidates.append(candidate)
        
        # Strategy 4: Enable cloud offloading if network allows
        if (hardware_profile.network.max_bandwidth_mbps >= 50 and
            'limited_bandwidth' not in base_prediction.bottlenecks):
            candidate = self._enable_cloud_offloading(base_config)
            optimization_candidates.append(candidate)
        
        # Evaluate all candidates
        best_config = base_config
        best_score = base_prediction.predicted_metrics.get('overall_score', 0)
        
        for candidate in optimization_candidates:
            candidate_prediction = self.classifier.predict_performance(hardware_profile, candidate)
            candidate_score = candidate_prediction.predicted_metrics.get('overall_score', 0)
            
            if candidate_score > best_score:
                best_config = candidate
                best_score = candidate_score
        
        return best_config
    
    def _apply_minor_optimizations(self, 
                                 config: AdaptiveConfiguration,
                                 prediction: PerformancePrediction) -> AdaptiveConfiguration:
        """Apply minor optimizations for already good configurations"""
        
        # Fine-tune cache size
        if 'slow_storage' not in prediction.bottlenecks:
            config.cache_size_mb = int(config.cache_size_mb * 1.2)
        
        # Fine-tune CPU target
        if prediction.predicted_metrics.get('cpu_utilization', 50) < 60:
            config.cpu_utilization_target = min(80, config.cpu_utilization_target + 10)
        
        return config
    
    def _reduce_memory_usage(self, config: AdaptiveConfiguration) -> AdaptiveConfiguration:
        """Reduce memory usage in configuration"""
        
        new_config = self._copy_configuration(config)
        new_config.memory_allocation_mb = int(new_config.memory_allocation_mb * 0.7)
        new_config.cache_size_mb = int(new_config.cache_size_mb * 0.5)
        new_config.max_concurrent_tasks = max(1, new_config.max_concurrent_tasks - 1)
        
        # Reduce UI complexity if needed
        if new_config.ui_complexity == "rich":
            new_config.ui_complexity = "standard"
        elif new_config.ui_complexity == "standard":
            new_config.ui_complexity = "basic"
        
        return new_config
    
    def _reduce_parallelism(self, config: AdaptiveConfiguration) -> AdaptiveConfiguration:
        """Reduce parallelism in configuration"""
        
        new_config = self._copy_configuration(config)
        new_config.processing_threads = max(1, new_config.processing_threads // 2)
        new_config.max_concurrent_tasks = max(1, new_config.max_concurrent_tasks - 1)
        
        return new_config
    
    def _disable_expensive_features(self, config: AdaptiveConfiguration) -> AdaptiveConfiguration:
        """Disable expensive features"""
        
        new_config = self._copy_configuration(config)
        new_config.ml_acceleration = False
        new_config.animation_level = "none"
        new_config.asset_quality = "low"
        new_config.ui_complexity = "basic"
        
        return new_config
    
    def _enable_cloud_offloading(self, config: AdaptiveConfiguration) -> AdaptiveConfiguration:
        """Enable cloud offloading"""
        
        new_config = self._copy_configuration(config)
        new_config.cloud_fallback = True
        new_config.compute_distribution = ComputeDistribution.CLOUD_HEAVY
        new_config.offline_mode = False
        
        return new_config
    
    def _copy_configuration(self, config: AdaptiveConfiguration) -> AdaptiveConfiguration:
        """Create a copy of configuration for modification"""
        
        # Create new configuration with same parameters
        return AdaptiveConfiguration(
            config_id=config.config_id + "_opt",
            interface_type=config.interface_type,
            compute_distribution=config.compute_distribution,
            ui_complexity=config.ui_complexity,
            animation_level=config.animation_level,
            asset_quality=config.asset_quality,
            responsive_breakpoints=config.responsive_breakpoints.copy(),
            max_concurrent_tasks=config.max_concurrent_tasks,
            memory_allocation_mb=config.memory_allocation_mb,
            cache_size_mb=config.cache_size_mb,
            processing_threads=config.processing_threads,
            cpu_utilization_target=config.cpu_utilization_target,
            memory_utilization_target=config.memory_utilization_target,
            power_profile=config.power_profile,
            thermal_management=config.thermal_management,
            optimization_goals=config.optimization_goals.copy(),
            ml_acceleration=config.ml_acceleration,
            cloud_fallback=config.cloud_fallback,
            offline_mode=config.offline_mode,
            predicted_performance=config.predicted_performance.copy(),
            estimated_resource_usage=config.estimated_resource_usage.copy(),
            confidence_score=config.confidence_score
        )
    
    def _determine_ui_complexity(self, hardware_profile: HardwareProfile,
                               interface_type: InterfaceType) -> str:
        """Determine UI complexity level"""
        
        if interface_type in [InterfaceType.MINIMAL, InterfaceType.TEXT_ONLY]:
            return "minimal"
        elif interface_type == InterfaceType.COMPACT:
            return "basic"
        elif hardware_profile.system_tier in [SystemTier.HIGH_END, SystemTier.ENTERPRISE]:
            return "rich"
        else:
            return "standard"
    
    def _determine_animation_level(self, hardware_profile: HardwareProfile,
                                 interface_type: InterfaceType) -> str:
        """Determine animation complexity level"""
        
        if interface_type == InterfaceType.MINIMAL:
            return "none"
        elif hardware_profile.system_tier == SystemTier.BASIC:
            return "minimal"
        elif hardware_profile.gpu and hardware_profile.memory.total_gb >= 8:
            return "rich"
        else:
            return "standard"
    
    def _determine_asset_quality(self, hardware_profile: HardwareProfile,
                               interface_type: InterfaceType) -> str:
        """Determine asset quality level"""
        
        if interface_type in [InterfaceType.MINIMAL, InterfaceType.TEXT_ONLY]:
            return "minimal"
        elif hardware_profile.memory.total_gb < 4:
            return "low"
        elif hardware_profile.system_tier == SystemTier.HIGH_END and hardware_profile.gpu:
            return "high"
        else:
            return "medium"
    
    def _analyze_performance_gaps(self, predicted: Dict[str, float],
                                actual: Dict[str, float]) -> Dict[str, float]:
        """Analyze gaps between predicted and actual performance"""
        
        gaps = {}
        for metric in predicted:
            if metric in actual:
                gaps[metric] = actual[metric] - predicted[metric]
        
        return gaps
    
    async def _generate_optimizations(self,
                                    config: AdaptiveConfiguration,
                                    hardware_profile: HardwareProfile,
                                    performance_gaps: Dict[str, float],
                                    user_feedback: Optional[Dict]) -> Dict[str, Any]:
        """Generate optimization recommendations"""
        
        optimizations = {}
        
        # If overall performance is below expected
        if performance_gaps.get('overall_score', 0) < -10:
            optimizations['reduce_complexity'] = True
            optimizations['disable_features'] = ['ml_acceleration', 'rich_animations']
        
        # If CPU utilization is too high
        if performance_gaps.get('cpu_utilization', 0) > 20:
            optimizations['reduce_parallelism'] = True
            optimizations['lower_cpu_target'] = True
        
        # If memory utilization is too high
        if performance_gaps.get('memory_utilization', 0) > 20:
            optimizations['reduce_memory_allocation'] = True
            optimizations['reduce_cache_size'] = True
        
        # User feedback adjustments
        if user_feedback:
            if user_feedback.get('too_slow', False):
                optimizations['increase_performance'] = True
            if user_feedback.get('battery_drain', False):
                optimizations['enable_power_saving'] = True
        
        return optimizations
    
    def _apply_optimizations(self, config: AdaptiveConfiguration,
                           optimizations: Dict[str, Any]) -> AdaptiveConfiguration:
        """Apply optimizations to configuration"""
        
        new_config = self._copy_configuration(config)
        
        if optimizations.get('reduce_complexity'):
            if new_config.ui_complexity == "rich":
                new_config.ui_complexity = "standard"
            elif new_config.ui_complexity == "standard":
                new_config.ui_complexity = "basic"
        
        if optimizations.get('reduce_parallelism'):
            new_config.processing_threads = max(1, new_config.processing_threads - 1)
            new_config.max_concurrent_tasks = max(1, new_config.max_concurrent_tasks - 1)
        
        if optimizations.get('reduce_memory_allocation'):
            new_config.memory_allocation_mb = int(new_config.memory_allocation_mb * 0.8)
        
        if optimizations.get('reduce_cache_size'):
            new_config.cache_size_mb = int(new_config.cache_size_mb * 0.7)
        
        if optimizations.get('enable_power_saving'):
            new_config.power_profile = "efficiency"
            new_config.cpu_utilization_target = min(50, new_config.cpu_utilization_target)
        
        return new_config
    
    def _calculate_confidence_score(self, prediction: PerformancePrediction) -> float:
        """Calculate confidence score for configuration"""
        
        # Base confidence on prediction quality
        confidence = 0.7  # Base confidence
        
        # Reduce confidence if many bottlenecks detected
        if len(prediction.bottlenecks) > 2:
            confidence -= 0.2
        
        # Increase confidence if no bottlenecks
        if prediction.bottlenecks == ['none_detected']:
            confidence += 0.2
        
        # Adjust based on prediction score
        score = prediction.predicted_metrics.get('overall_score', 75)
        if score > 85:
            confidence += 0.1
        elif score < 60:
            confidence -= 0.2
        
        return max(0.1, min(1.0, confidence))
    
    def _cache_configuration(self, config: AdaptiveConfiguration):
        """Cache configuration for reuse"""
        
        self.optimization_cache[config.config_id] = {
            'configuration': config,
            'timestamp': datetime.now()
        }
        
        # Limit cache size
        if len(self.optimization_cache) > 100:
            # Remove oldest entries
            sorted_items = sorted(
                self.optimization_cache.items(), 
                key=lambda x: x[1]['timestamp']
            )
            for old_key, _ in sorted_items[:10]:
                del self.optimization_cache[old_key]