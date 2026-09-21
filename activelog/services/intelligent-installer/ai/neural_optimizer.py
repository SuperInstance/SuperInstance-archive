"""
Advanced Neural Network Optimizer
Next-generation AI-powered configuration optimization using deep learning
"""

import asyncio
import numpy as np
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import pickle
from pathlib import Path

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # Fallback to basic ML
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor

from api.models import HardwareProfile, AdaptiveConfiguration, OptimizationGoal

@dataclass
class OptimizationContext:
    """Rich context for optimization decisions"""
    hardware_profile: HardwareProfile
    user_preferences: Dict[str, Any]
    historical_performance: List[Dict[str, float]]
    current_workload: Dict[str, float]
    network_conditions: Dict[str, float]
    power_constraints: Dict[str, float]
    thermal_conditions: Dict[str, float]
    user_behavior_patterns: Dict[str, Any]
    time_context: Dict[str, Any]
    application_requirements: Dict[str, Any]

class DeepConfigurationNet(nn.Module):
    """Deep neural network for configuration optimization"""
    
    def __init__(self, input_size: int = 128, hidden_sizes: List[int] = None):
        super(DeepConfigurationNet, self).__init__()
        
        if hidden_sizes is None:
            hidden_sizes = [256, 512, 256, 128, 64]
        
        # Build network layers
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.BatchNorm1d(hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Output layers for different configuration aspects
        self.feature_extractor = nn.Sequential(*layers)
        
        # Multiple heads for different optimization targets
        self.performance_head = nn.Linear(prev_size, 32)
        self.efficiency_head = nn.Linear(prev_size, 32)
        self.stability_head = nn.Linear(prev_size, 32)
        self.user_satisfaction_head = nn.Linear(prev_size, 16)
        
        # Final configuration parameters
        self.config_output = nn.Linear(32 + 32 + 32 + 16, 64)
        
        # Attention mechanism for context weighting
        self.attention = nn.MultiheadAttention(embed_dim=64, num_heads=8)
        
    def forward(self, x: torch.Tensor, context_mask: Optional[torch.Tensor] = None):
        # Extract features
        features = self.feature_extractor(x)
        
        # Multi-head outputs
        performance_features = self.performance_head(features)
        efficiency_features = self.efficiency_head(features)
        stability_features = self.stability_head(features)
        satisfaction_features = self.user_satisfaction_head(features)
        
        # Combine features
        combined_features = torch.cat([
            performance_features, efficiency_features, 
            stability_features, satisfaction_features
        ], dim=-1)
        
        # Generate configuration
        config_params = self.config_output(combined_features)
        
        # Apply attention if needed
        if context_mask is not None:
            config_params = config_params.unsqueeze(0)  # Add sequence dimension
            attended_config, _ = self.attention(config_params, config_params, config_params)
            config_params = attended_config.squeeze(0)
        
        return {
            'configuration_parameters': config_params,
            'performance_score': torch.sigmoid(performance_features.mean(dim=-1)),
            'efficiency_score': torch.sigmoid(efficiency_features.mean(dim=-1)),
            'stability_score': torch.sigmoid(stability_features.mean(dim=-1)),
            'satisfaction_score': torch.sigmoid(satisfaction_features.mean(dim=-1))
        }

class ReinforcementLearningOptimizer:
    """Reinforcement Learning based configuration optimizer"""
    
    def __init__(self):
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.exploration_rate = 0.1
        self.experience_buffer = []
        self.max_buffer_size = 10000
        
    def get_state_key(self, context: OptimizationContext) -> str:
        """Convert optimization context to state key"""
        
        # Discretize continuous values for state representation
        cpu_tier = min(4, int(context.hardware_profile.cpu.cores / 4))
        memory_tier = min(4, int(context.hardware_profile.memory.total_gb / 8))
        gpu_tier = 2 if context.hardware_profile.gpu else 0
        
        workload_intensity = "high" if context.current_workload.get('cpu_percent', 0) > 70 else "low"
        power_mode = context.power_constraints.get('mode', 'balanced')
        
        return f"{cpu_tier}_{memory_tier}_{gpu_tier}_{workload_intensity}_{power_mode}"
    
    def get_action_space(self) -> List[Dict[str, Any]]:
        """Define possible configuration actions"""
        
        return [
            {'interface_complexity': 'minimal', 'compute_distribution': 'local_100'},
            {'interface_complexity': 'basic', 'compute_distribution': 'local_100'},
            {'interface_complexity': 'standard', 'compute_distribution': 'hybrid_balanced'},
            {'interface_complexity': 'rich', 'compute_distribution': 'hybrid_balanced'},
            {'interface_complexity': 'standard', 'compute_distribution': 'cloud_heavy'},
            {'interface_complexity': 'rich', 'compute_distribution': 'cloud_heavy'},
            {'interface_complexity': 'minimal', 'compute_distribution': 'edge_optimized'},
            {'interface_complexity': 'basic', 'compute_distribution': 'opportunistic'}
        ]
    
    def choose_action(self, state_key: str) -> Dict[str, Any]:
        """Choose action using epsilon-greedy policy"""
        
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0] * len(self.get_action_space())
        
        if np.random.random() < self.exploration_rate:
            # Explore: choose random action
            action_idx = np.random.choice(len(self.get_action_space()))
        else:
            # Exploit: choose best action
            action_idx = np.argmax(self.q_table[state_key])
        
        return action_idx, self.get_action_space()[action_idx]
    
    def update_q_table(self, state_key: str, action_idx: int, reward: float, 
                      next_state_key: Optional[str] = None):
        """Update Q-table based on experience"""
        
        if state_key not in self.q_table:
            self.q_table[state_key] = [0.0] * len(self.get_action_space())
        
        current_q = self.q_table[state_key][action_idx]
        
        if next_state_key and next_state_key in self.q_table:
            # Q-learning update
            max_next_q = max(self.q_table[next_state_key])
            new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        else:
            # Simple reward-based update
            new_q = current_q + self.learning_rate * (reward - current_q)
        
        self.q_table[state_key][action_idx] = new_q
        
        # Store experience
        self.experience_buffer.append({
            'state': state_key,
            'action': action_idx,
            'reward': reward,
            'next_state': next_state_key,
            'timestamp': datetime.now()
        })
        
        # Limit buffer size
        if len(self.experience_buffer) > self.max_buffer_size:
            self.experience_buffer = self.experience_buffer[-self.max_buffer_size:]

class NeuralOptimizer:
    """Advanced neural network-based configuration optimizer"""
    
    def __init__(self):
        self.model = None
        self.rl_optimizer = ReinforcementLearningOptimizer()
        self.training_data = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') if TORCH_AVAILABLE else None
        self.is_trained = False
        self.model_version = "1.0.0"
        
    async def initialize(self):
        """Initialize the neural optimizer"""
        
        if TORCH_AVAILABLE:
            # Initialize deep learning model
            self.model = DeepConfigurationNet(input_size=128)
            if torch.cuda.is_available():
                self.model = self.model.cuda()
            
            # Try to load pre-trained model
            await self._load_pretrained_model()
            
            logging.info("🧠 Neural optimizer initialized with PyTorch support")
        else:
            # Fallback to sklearn
            from sklearn.ensemble import RandomForestRegressor
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
            logging.info("🧠 Neural optimizer initialized with sklearn fallback")
    
    async def optimize_configuration(self, context: OptimizationContext) -> Dict[str, Any]:
        """Generate optimized configuration using neural networks"""
        
        # Extract features from context
        features = self._extract_features(context)
        
        if TORCH_AVAILABLE and isinstance(self.model, DeepConfigurationNet):
            # Use deep learning model
            optimization_result = await self._deep_optimize(features, context)
        else:
            # Use traditional ML
            optimization_result = await self._traditional_optimize(features, context)
        
        # Apply reinforcement learning refinement
        rl_refinement = await self._apply_rl_refinement(context, optimization_result)
        
        # Combine results
        final_optimization = self._combine_optimizations(optimization_result, rl_refinement)
        
        return final_optimization
    
    def _extract_features(self, context: OptimizationContext) -> np.ndarray:
        """Extract numerical features from optimization context"""
        
        features = []
        
        # Hardware features (32 features)
        hw = context.hardware_profile
        features.extend([
            hw.cpu.cores, hw.cpu.threads, hw.cpu.base_frequency_ghz,
            hw.memory.total_gb, hw.memory.available_gb,
            1.0 if hw.gpu else 0.0, hw.gpu.memory_gb if hw.gpu else 0.0,
            hw.storage.total_capacity_gb / 1000,  # Normalize to TB
            hw.storage.available_capacity_gb / 1000,
            1.0 if hw.storage.primary_type == 'SSD' else 0.0,
            hw.network.max_bandwidth_mbps / 1000,  # Normalize to Gbps
            hw.display.total_pixels / 1000000 if hw.display else 0,  # Normalize to millions
            1.0 if hw.power and hw.power.battery_present else 0.0,
            hw.power.battery_health_percent / 100 if hw.power else 1.0,
            # System tier encoding
            {'embedded': 1, 'basic': 2, 'standard': 3, 'high_end': 4, 'enterprise': 5, 'specialized': 6}.get(hw.system_tier.value, 3),
            # Pad to 32 features
            *([0.0] * 17)
        ])
        
        # User preferences (16 features)
        prefs = context.user_preferences
        features.extend([
            1.0 if prefs.get('performance_priority', False) else 0.0,
            1.0 if prefs.get('privacy_sensitive', False) else 0.0,
            1.0 if prefs.get('cost_conscious', False) else 0.0,
            1.0 if prefs.get('battery_conservation', False) else 0.0,
            prefs.get('ui_complexity_preference', 0.5),
            prefs.get('automation_level', 0.5),
            *([0.0] * 10)  # Pad to 16 features
        ])
        
        # Historical performance (16 features)
        if context.historical_performance:
            recent_perf = context.historical_performance[-5:]  # Last 5 measurements
            avg_performance = np.mean([p.get('overall_score', 75) for p in recent_perf]) / 100
            performance_trend = self._calculate_trend([p.get('overall_score', 75) for p in recent_perf])
            performance_stability = 1 - np.std([p.get('overall_score', 75) for p in recent_perf]) / 100
            features.extend([avg_performance, performance_trend, performance_stability, *([0.0] * 13)])
        else:
            features.extend([0.75, 0.0, 0.8, *([0.0] * 13)])
        
        # Current workload (16 features)
        workload = context.current_workload
        features.extend([
            workload.get('cpu_percent', 50) / 100,
            workload.get('memory_percent', 50) / 100,
            workload.get('disk_usage', 50) / 100,
            workload.get('network_usage', 10) / 100,
            workload.get('gpu_usage', 0) / 100,
            *([0.0] * 11)
        ])
        
        # Environmental context (16 features) 
        features.extend([
            context.network_conditions.get('bandwidth_score', 0.7),
            context.network_conditions.get('latency_score', 0.7),
            context.network_conditions.get('stability_score', 0.8),
            context.power_constraints.get('battery_level', 1.0),
            context.thermal_conditions.get('temperature_normalized', 0.5),
            context.thermal_conditions.get('throttling_risk', 0.0),
            *([0.0] * 10)
        ])
        
        # Time and behavior context (16 features)
        time_ctx = context.time_context
        behavior = context.user_behavior_patterns
        features.extend([
            time_ctx.get('hour_normalized', 0.5),  # 0-1 for hour of day
            time_ctx.get('day_of_week', 3) / 7,
            1.0 if time_ctx.get('is_work_hours', False) else 0.0,
            behavior.get('interaction_frequency', 0.5),
            behavior.get('power_user_score', 0.3),
            behavior.get('patience_score', 0.7),
            *([0.0] * 10)
        ])
        
        # Application requirements (16 features)
        app_reqs = context.application_requirements
        features.extend([
            app_reqs.get('cpu_intensive', 0.0),
            app_reqs.get('memory_requirement_normalized', 0.3),
            app_reqs.get('gpu_requirement', 0.0),
            app_reqs.get('network_requirement', 0.2),
            app_reqs.get('real_time_requirement', 0.0),
            app_reqs.get('security_requirement', 0.5),
            *([0.0] * 10)
        ])
        
        return np.array(features[:128])  # Ensure exactly 128 features
    
    async def _deep_optimize(self, features: np.ndarray, context: OptimizationContext) -> Dict[str, Any]:
        """Optimize using deep learning model"""
        
        if not self.is_trained:
            # Use heuristic optimization if model not trained
            return await self._heuristic_optimize(features, context)
        
        with torch.no_grad():
            # Convert to tensor
            feature_tensor = torch.FloatTensor(features).unsqueeze(0)
            if torch.cuda.is_available():
                feature_tensor = feature_tensor.cuda()
            
            # Forward pass
            outputs = self.model(feature_tensor)
            
            # Extract configuration parameters
            config_params = outputs['configuration_parameters'].cpu().numpy().flatten()
            
            # Convert to configuration
            optimization = self._params_to_config(config_params, context)
            optimization.update({
                'predicted_performance': float(outputs['performance_score'].cpu()),
                'predicted_efficiency': float(outputs['efficiency_score'].cpu()),
                'predicted_stability': float(outputs['stability_score'].cpu()),
                'predicted_satisfaction': float(outputs['satisfaction_score'].cpu()),
                'optimization_method': 'deep_learning',
                'confidence': 0.85
            })
            
            return optimization
    
    async def _traditional_optimize(self, features: np.ndarray, context: OptimizationContext) -> Dict[str, Any]:
        """Optimize using traditional ML"""
        
        # Use heuristic rules combined with simple ML
        return await self._heuristic_optimize(features, context)
    
    async def _heuristic_optimize(self, features: np.ndarray, context: OptimizationContext) -> Dict[str, Any]:
        """Heuristic-based optimization"""
        
        hw = context.hardware_profile
        prefs = context.user_preferences
        workload = context.current_workload
        
        # Determine optimal configuration based on heuristics
        optimization = {
            'interface_type': 'standard',
            'compute_distribution': 'hybrid_balanced',
            'ui_complexity': 'standard',
            'performance_mode': 'balanced',
            'optimization_method': 'heuristic',
            'confidence': 0.7
        }
        
        # Hardware-based adjustments
        if hw.system_tier.value in ['embedded', 'basic']:
            optimization.update({
                'interface_type': 'minimal',
                'ui_complexity': 'minimal',
                'compute_distribution': 'local_100'
            })
        elif hw.system_tier.value in ['high_end', 'enterprise']:
            optimization.update({
                'interface_type': 'full_hd',
                'ui_complexity': 'rich',
                'compute_distribution': 'hybrid_balanced'
            })
        
        # Performance preference adjustments
        if prefs.get('performance_priority', False):
            optimization.update({
                'performance_mode': 'performance',
                'compute_distribution': 'local_100' if hw.gpu else 'cloud_heavy'
            })
        
        # Battery conservation adjustments
        if prefs.get('battery_conservation', False):
            optimization.update({
                'performance_mode': 'efficiency',
                'ui_complexity': 'basic'
            })
        
        # Workload-based adjustments
        cpu_usage = workload.get('cpu_percent', 50)
        if cpu_usage > 80:
            optimization['compute_distribution'] = 'cloud_heavy'
        elif cpu_usage < 30:
            optimization['performance_mode'] = 'efficiency'
        
        return optimization
    
    async def _apply_rl_refinement(self, context: OptimizationContext, base_optimization: Dict[str, Any]) -> Dict[str, Any]:
        """Apply reinforcement learning refinement"""
        
        state_key = self.rl_optimizer.get_state_key(context)
        action_idx, rl_action = self.rl_optimizer.choose_action(state_key)
        
        # Combine RL suggestions with base optimization
        refined_optimization = base_optimization.copy()
        refined_optimization.update(rl_action)
        refined_optimization['rl_state'] = state_key
        refined_optimization['rl_action'] = action_idx
        
        return refined_optimization
    
    def _combine_optimizations(self, base: Dict[str, Any], rl: Dict[str, Any]) -> Dict[str, Any]:
        """Combine different optimization results"""
        
        # Weight the optimizations based on confidence
        base_weight = base.get('confidence', 0.7)
        rl_weight = 0.3
        
        combined = base.copy()
        
        # Use RL suggestions for specific parameters
        if rl.get('interface_complexity'):
            combined['ui_complexity'] = rl['interface_complexity']
        if rl.get('compute_distribution'):
            combined['compute_distribution'] = rl['compute_distribution']
        
        # Update metadata
        combined.update({
            'optimization_method': 'neural_hybrid',
            'base_confidence': base_weight,
            'rl_influence': rl_weight,
            'combined_confidence': (base_weight + rl_weight) / 2
        })
        
        return combined
    
    def _params_to_config(self, params: np.ndarray, context: OptimizationContext) -> Dict[str, Any]:
        """Convert neural network parameters to configuration"""
        
        # Map parameter ranges to configuration options
        interface_score = params[0]
        compute_score = params[1] 
        complexity_score = params[2]
        performance_score = params[3]
        
        # Map scores to discrete choices
        interface_types = ['minimal', 'compact', 'standard', 'full_hd']
        interface_type = interface_types[min(len(interface_types)-1, int(interface_score * len(interface_types)))]
        
        compute_types = ['local_100', 'hybrid_balanced', 'cloud_heavy', 'edge_optimized']
        compute_distribution = compute_types[min(len(compute_types)-1, int(compute_score * len(compute_types)))]
        
        complexity_levels = ['minimal', 'basic', 'standard', 'rich']
        ui_complexity = complexity_levels[min(len(complexity_levels)-1, int(complexity_score * len(complexity_levels)))]
        
        performance_modes = ['efficiency', 'balanced', 'performance']
        performance_mode = performance_modes[min(len(performance_modes)-1, int(performance_score * len(performance_modes)))]
        
        return {
            'interface_type': interface_type,
            'compute_distribution': compute_distribution,
            'ui_complexity': ui_complexity,
            'performance_mode': performance_mode
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction (-1 to 1)"""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = np.arange(n)
        slope = np.corrcoef(x, values)[0, 1] if n > 1 else 0.0
        
        return np.clip(slope, -1.0, 1.0)
    
    async def record_optimization_result(self, context: OptimizationContext, 
                                       optimization: Dict[str, Any], 
                                       performance_result: Dict[str, float]):
        """Record optimization result for learning"""
        
        # Calculate reward for reinforcement learning
        reward = self._calculate_reward(performance_result, context.user_preferences)
        
        # Update RL model if applicable
        if 'rl_state' in optimization and 'rl_action' in optimization:
            self.rl_optimizer.update_q_table(
                optimization['rl_state'],
                optimization['rl_action'],
                reward
            )
        
        # Store training data for deep learning
        if TORCH_AVAILABLE:
            features = self._extract_features(context)
            self.training_data.append({
                'features': features,
                'optimization': optimization,
                'performance': performance_result,
                'reward': reward,
                'timestamp': datetime.now()
            })
            
            # Retrain periodically
            if len(self.training_data) > 100 and len(self.training_data) % 50 == 0:
                await self._retrain_model()
    
    def _calculate_reward(self, performance_result: Dict[str, float], preferences: Dict[str, Any]) -> float:
        """Calculate reward for reinforcement learning"""
        
        base_reward = performance_result.get('overall_score', 75) / 100
        
        # Adjust reward based on preferences
        if preferences.get('performance_priority', False):
            performance_factor = performance_result.get('performance_score', base_reward)
            base_reward = base_reward * 0.7 + performance_factor * 0.3
        
        if preferences.get('battery_conservation', False):
            efficiency_factor = performance_result.get('efficiency_score', base_reward)
            base_reward = base_reward * 0.7 + efficiency_factor * 0.3
        
        return base_reward
    
    async def _retrain_model(self):
        """Retrain the neural network model"""
        
        if not TORCH_AVAILABLE or len(self.training_data) < 50:
            return
        
        try:
            # Prepare training data
            features = np.array([item['features'] for item in self.training_data[-500:]])  # Last 500 samples
            rewards = np.array([item['reward'] for item in self.training_data[-500:]])
            
            # Convert to tensors
            feature_tensor = torch.FloatTensor(features)
            reward_tensor = torch.FloatTensor(rewards)
            
            if torch.cuda.is_available():
                feature_tensor = feature_tensor.cuda()
                reward_tensor = reward_tensor.cuda()
            
            # Training setup
            self.model.train()
            optimizer = optim.Adam(self.model.parameters(), lr=0.001)
            criterion = nn.MSELoss()
            
            # Training loop
            for epoch in range(10):
                optimizer.zero_grad()
                
                outputs = self.model(feature_tensor)
                # Use performance score as proxy for overall optimization quality
                loss = criterion(outputs['performance_score'], reward_tensor)
                
                loss.backward()
                optimizer.step()
            
            self.model.eval()
            self.is_trained = True
            
            logging.info(f"🧠 Neural model retrained with {len(features)} samples")
            
        except Exception as e:
            logging.error(f"Failed to retrain model: {e}")
    
    async def _load_pretrained_model(self):
        """Load pre-trained model if available"""
        
        model_path = Path("models/neural_optimizer.pt")
        if model_path.exists():
            try:
                checkpoint = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(checkpoint['model_state'])
                self.model_version = checkpoint.get('version', '1.0.0')
                self.is_trained = True
                logging.info(f"🧠 Loaded pre-trained model v{self.model_version}")
            except Exception as e:
                logging.warning(f"Failed to load pre-trained model: {e}")
    
    async def save_model(self):
        """Save the current model"""
        
        if not TORCH_AVAILABLE or not self.is_trained:
            return
        
        model_path = Path("models")
        model_path.mkdir(exist_ok=True)
        
        try:
            checkpoint = {
                'model_state': self.model.state_dict(),
                'version': self.model_version,
                'training_samples': len(self.training_data),
                'saved_at': datetime.now().isoformat()
            }
            
            torch.save(checkpoint, model_path / "neural_optimizer.pt")
            
            # Also save RL Q-table
            with open(model_path / "rl_qtable.json", 'w') as f:
                json.dump(self.rl_optimizer.q_table, f)
            
            logging.info("🧠 Neural models saved successfully")
            
        except Exception as e:
            logging.error(f"Failed to save models: {e}")

class AdvancedOptimizer:
    """Advanced optimizer combining multiple AI techniques"""
    
    def __init__(self):
        self.neural_optimizer = NeuralOptimizer()
        self.context_cache = {}
        self.optimization_history = []
        
    async def initialize(self):
        """Initialize the advanced optimizer"""
        await self.neural_optimizer.initialize()
        logging.info("🚀 Advanced AI optimizer initialized")
    
    async def optimize(self, hardware_profile: HardwareProfile,
                     user_preferences: Dict[str, Any] = None,
                     application_requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform advanced optimization"""
        
        # Build rich optimization context
        context = await self._build_optimization_context(
            hardware_profile, user_preferences or {}, application_requirements or {}
        )
        
        # Perform neural optimization
        optimization_result = await self.neural_optimizer.optimize_configuration(context)
        
        # Post-process and validate
        final_result = await self._post_process_optimization(optimization_result, context)
        
        # Cache for future reference
        self.context_cache[hardware_profile.profile_id] = context
        self.optimization_history.append({
            'context': context,
            'result': final_result,
            'timestamp': datetime.now()
        })
        
        return final_result
    
    async def _build_optimization_context(self, hardware_profile: HardwareProfile,
                                        user_preferences: Dict[str, Any],
                                        application_requirements: Dict[str, Any]) -> OptimizationContext:
        """Build comprehensive optimization context"""
        
        # Get current system state
        current_workload = await self._get_current_workload()
        network_conditions = await self._assess_network_conditions()
        power_constraints = await self._assess_power_constraints(hardware_profile)
        thermal_conditions = await self._assess_thermal_conditions()
        
        # Analyze user behavior patterns
        user_behavior_patterns = await self._analyze_user_behavior(hardware_profile.profile_id)
        
        # Get time context
        now = datetime.now()
        time_context = {
            'hour_normalized': now.hour / 24.0,
            'day_of_week': now.weekday(),
            'is_work_hours': 9 <= now.hour <= 17,
            'is_weekend': now.weekday() >= 5
        }
        
        # Get historical performance
        historical_performance = await self._get_historical_performance(hardware_profile.profile_id)
        
        return OptimizationContext(
            hardware_profile=hardware_profile,
            user_preferences=user_preferences,
            historical_performance=historical_performance,
            current_workload=current_workload,
            network_conditions=network_conditions,
            power_constraints=power_constraints,
            thermal_conditions=thermal_conditions,
            user_behavior_patterns=user_behavior_patterns,
            time_context=time_context,
            application_requirements=application_requirements
        )
    
    async def _get_current_workload(self) -> Dict[str, float]:
        """Get current system workload"""
        try:
            import psutil
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'network_usage': 10.0,  # Placeholder
                'gpu_usage': 0.0  # Placeholder
            }
        except Exception:
            return {'cpu_percent': 50, 'memory_percent': 60, 'disk_usage': 70}
    
    async def _assess_network_conditions(self) -> Dict[str, float]:
        """Assess current network conditions"""
        # Placeholder implementation
        return {
            'bandwidth_score': 0.8,
            'latency_score': 0.7,
            'stability_score': 0.9,
            'quality_score': 0.8
        }
    
    async def _assess_power_constraints(self, hardware_profile: HardwareProfile) -> Dict[str, float]:
        """Assess power constraints"""
        power_info = hardware_profile.power
        if power_info and power_info.battery_present:
            return {
                'battery_level': (power_info.battery_health_percent or 50) / 100,
                'power_saving_required': 1.0 if power_info.battery_health_percent and power_info.battery_health_percent < 30 else 0.0,
                'mode': 'battery'
            }
        else:
            return {
                'battery_level': 1.0,
                'power_saving_required': 0.0,
                'mode': 'plugged'
            }
    
    async def _assess_thermal_conditions(self) -> Dict[str, float]:
        """Assess thermal conditions"""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                max_temp = 0
                for name, entries in temps.items():
                    for entry in entries:
                        max_temp = max(max_temp, entry.current)
                
                return {
                    'temperature_normalized': min(1.0, max_temp / 100.0),
                    'throttling_risk': 1.0 if max_temp > 85 else 0.0,
                    'cooling_efficiency': 1.0 - (max_temp / 100.0)
                }
        except Exception:
            pass
        
        return {
            'temperature_normalized': 0.5,
            'throttling_risk': 0.0,
            'cooling_efficiency': 0.8
        }
    
    async def _analyze_user_behavior(self, profile_id: str) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        # Placeholder implementation
        return {
            'interaction_frequency': 0.6,
            'power_user_score': 0.4,
            'patience_score': 0.7,
            'preferred_complexity': 'standard',
            'typical_usage_duration': 120  # minutes
        }
    
    async def _get_historical_performance(self, profile_id: str) -> List[Dict[str, float]]:
        """Get historical performance data"""
        # Return recent optimization history for this profile
        recent_history = [
            opt for opt in self.optimization_history[-20:] 
            if opt['context'].hardware_profile.profile_id == profile_id
        ]
        
        return [
            {
                'overall_score': 85.0,
                'performance_score': 80.0,
                'efficiency_score': 90.0,
                'timestamp': opt['timestamp'].isoformat()
            }
            for opt in recent_history
        ]
    
    async def _post_process_optimization(self, optimization: Dict[str, Any], 
                                       context: OptimizationContext) -> Dict[str, Any]:
        """Post-process optimization results"""
        
        # Add validation and safety checks
        validated_optimization = optimization.copy()
        
        # Ensure compatibility with hardware
        if context.hardware_profile.system_tier.value == 'basic' and optimization.get('ui_complexity') == 'rich':
            validated_optimization['ui_complexity'] = 'standard'
            validated_optimization['compatibility_adjustment'] = 'downgraded_ui_for_basic_hardware'
        
        # Add explanation
        validated_optimization['explanation'] = self._generate_optimization_explanation(validated_optimization, context)
        
        # Add confidence intervals
        validated_optimization['confidence_interval'] = {
            'lower_bound': max(0.0, validated_optimization.get('combined_confidence', 0.7) - 0.1),
            'upper_bound': min(1.0, validated_optimization.get('combined_confidence', 0.7) + 0.1)
        }
        
        return validated_optimization
    
    def _generate_optimization_explanation(self, optimization: Dict[str, Any], 
                                         context: OptimizationContext) -> str:
        """Generate human-readable explanation"""
        
        explanations = []
        
        hw_tier = context.hardware_profile.system_tier.value
        ui_complexity = optimization.get('ui_complexity', 'standard')
        compute_dist = optimization.get('compute_distribution', 'hybrid_balanced')
        
        explanations.append(f"Detected {hw_tier} hardware configuration")
        
        if ui_complexity == 'minimal':
            explanations.append("Optimized for lightweight interface to conserve resources")
        elif ui_complexity == 'rich':
            explanations.append("Enabled rich interface features for enhanced user experience")
        
        if compute_dist == 'local_100':
            explanations.append("Configured for local processing to ensure privacy and reduce latency")
        elif compute_dist == 'cloud_heavy':
            explanations.append("Leveraging cloud resources for compute-intensive tasks")
        elif compute_dist == 'hybrid_balanced':
            explanations.append("Balanced local and cloud processing for optimal performance")
        
        return ". ".join(explanations) + "."