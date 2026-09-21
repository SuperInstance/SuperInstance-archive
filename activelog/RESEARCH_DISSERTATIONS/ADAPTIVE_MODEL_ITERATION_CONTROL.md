# Adaptive Model Iteration Control: Self-Regulating Firefly Bot Loop Speeds

## Core Concept: Usage-Based Iteration Dynamics

Each firefly bot model controls its own iteration loop speed based on:
1. **Usage Tracking**: Whether it got selected/used in recent cycles
2. **Performance Recognition**: ML patterns indicating success or failure trends  
3. **Compute Allocation**: Dynamic share of total compute resources
4. **Stop Conditions**: ML-recognized patterns indicating model mismatch for current system

---

## Mathematical Framework for Adaptive Loop Speed

### Usage-Based Speed Control

```python
class AdaptiveIterationController:
    def __init__(self, base_iteration_speed=1.0):
        self.base_speed = base_iteration_speed
        self.current_speed = base_iteration_speed
        self.usage_history = []
        self.performance_tracker = ModelPerformanceTracker()
        self.ml_pattern_recognizer = MLPatternRecognizer()
        
    def calculate_iteration_speed(self):
        """Calculate next iteration speed based on usage and performance"""
        
        # 1. Usage-based speed adjustment
        recent_usage = self.get_recent_usage_rate(window=20)  # Last 20 cycles
        
        if recent_usage > 0.7:  # High demand
            usage_multiplier = min(2.0, 1.0 + recent_usage)  # Speed up to 2x
        elif recent_usage > 0.3:  # Moderate demand  
            usage_multiplier = 1.0  # Normal speed
        else:  # Low demand
            usage_multiplier = max(0.1, recent_usage * 2)  # Slow down to 10% minimum
        
        # 2. Performance-based adjustment
        performance_trend = self.performance_tracker.get_trend()
        
        if performance_trend == 'improving':
            performance_multiplier = 1.2  # Speed up improving models
        elif performance_trend == 'declining':
            performance_multiplier = 0.8  # Slow down declining models  
        else:
            performance_multiplier = 1.0  # Stable performance
        
        # 3. Compute allocation influence
        compute_share = self.get_current_compute_allocation()
        compute_multiplier = min(1.5, max(0.2, compute_share / 0.1))  # Scale with resources
        
        # 4. Combined speed calculation
        new_speed = (self.base_speed * 
                    usage_multiplier * 
                    performance_multiplier * 
                    compute_multiplier)
        
        # 5. Check for stop conditions
        if self.should_stop_model():
            new_speed = 0.01  # Near-zero speed for stopping models
            
        self.current_speed = new_speed
        return new_speed
    
    def get_recent_usage_rate(self, window=20):
        """Calculate usage rate over recent window"""
        if len(self.usage_history) < window:
            return 0.5  # Default for new models
            
        recent_usage = self.usage_history[-window:]
        return sum(recent_usage) / len(recent_usage)
    
    def should_stop_model(self):
        """ML-based pattern recognition for stopping conditions"""
        
        # Pattern 1: Consistent low usage with declining performance
        usage_pattern = self.ml_pattern_recognizer.analyze_usage_pattern(self.usage_history)
        performance_pattern = self.ml_pattern_recognizer.analyze_performance_pattern(
            self.performance_tracker.get_history()
        )
        
        if (usage_pattern == 'consistent_low' and 
            performance_pattern == 'declining' and
            len(self.usage_history) > 50):  # Sufficient data
            return True
            
        # Pattern 2: Resource inefficiency pattern
        efficiency_score = self.calculate_resource_efficiency()
        if efficiency_score < 0.1 and len(self.usage_history) > 30:
            return True
            
        # Pattern 3: System mismatch pattern
        mismatch_score = self.ml_pattern_recognizer.detect_system_mismatch(
            self.usage_history,
            self.performance_tracker.get_history(),
            self.get_neuron_feedback_patterns()
        )
        
        if mismatch_score > 0.8:  # High confidence of mismatch
            return True
            
        return False
```

---

## Independent Model Loop Architecture

### Self-Governing Iteration Cycles

```python
class IndependentFireflyModel:
    def __init__(self, model_id, model_type):
        self.model_id = model_id
        self.model_type = model_type
        self.iteration_controller = AdaptiveIterationController()
        self.compute_allocator = ComputeAllocator()
        self.usage_tracker = UsageTracker()
        
    def autonomous_iteration_loop(self):
        """Independent loop that adapts its own speed"""
        
        while not self.is_terminated:
            # Calculate current iteration speed
            loop_speed = self.iteration_controller.calculate_iteration_speed()
            
            if loop_speed < 0.05:  # Model stopping threshold
                self.initiate_model_retirement()
                break
                
            # Adjust sleep time based on speed
            iteration_delay = max(0.1, 1.0 / loop_speed)  # Faster speed = shorter delay
            
            # Execute one model iteration
            iteration_start = time.time()
            
            # 1. Check for firefly bot requests
            requests = self.check_for_requests()
            
            if requests:
                # Model got used - record usage
                self.usage_tracker.record_usage(True, len(requests))
                
                # Process requests with allocated compute
                compute_budget = self.compute_allocator.get_current_budget()
                results = self.process_requests(requests, compute_budget)
                
                # Update performance metrics
                self.iteration_controller.performance_tracker.update(results)
                
            else:
                # Model not used this cycle
                self.usage_tracker.record_usage(False, 0)
            
            # 2. Update iteration controller with usage data
            iteration_duration = time.time() - iteration_start
            self.iteration_controller.record_iteration(iteration_duration, bool(requests))
            
            # 3. Request compute resources based on usage
            self.request_compute_adjustment()
            
            # 4. Adaptive sleep based on calculated speed
            time.sleep(iteration_delay)
    
    def request_compute_adjustment(self):
        """Request compute allocation change based on usage patterns"""
        
        usage_trend = self.usage_tracker.get_usage_trend()
        performance_trend = self.iteration_controller.performance_tracker.get_trend()
        
        if usage_trend == 'increasing' and performance_trend == 'improving':
            # Request more compute resources
            requested_allocation = min(1.0, self.compute_allocator.current_allocation * 1.3)
            self.compute_allocator.request_allocation_change(requested_allocation)
            
        elif usage_trend == 'decreasing' or performance_trend == 'declining':
            # Offer to give up compute resources
            requested_allocation = max(0.1, self.compute_allocator.current_allocation * 0.8)
            self.compute_allocator.request_allocation_change(requested_allocation)
```

---

## ML Pattern Recognition for Model Stopping

### Stopping Condition Patterns

```python
class MLPatternRecognizer:
    def __init__(self):
        self.pattern_models = {
            'usage_decline': UsageDeclinePatternModel(),
            'performance_plateau': PerformancePlateauModel(),
            'system_mismatch': SystemMismatchModel(),
            'resource_inefficiency': ResourceInefficiencyModel()
        }
    
    def analyze_usage_pattern(self, usage_history):
        """Recognize patterns in usage history"""
        
        if len(usage_history) < 20:
            return 'insufficient_data'
            
        # Convert to features for ML analysis
        features = self.extract_usage_features(usage_history)
        
        # Check for various stopping patterns
        patterns = {}
        
        # Pattern 1: Consistent decline
        if self.detect_consistent_decline(usage_history):
            patterns['consistent_decline'] = True
            
        # Pattern 2: Cyclical low usage
        if self.detect_cyclical_low_usage(usage_history):
            patterns['cyclical_low'] = True
            
        # Pattern 3: Sudden abandonment
        if self.detect_sudden_abandonment(usage_history):
            patterns['sudden_abandonment'] = True
            
        # Pattern 4: Never took off
        if self.detect_never_gained_traction(usage_history):
            patterns['never_gained_traction'] = True
            
        return self.classify_usage_pattern(patterns)
    
    def detect_system_mismatch(self, usage_history, performance_history, neuron_feedback):
        """Detect if model is fundamentally mismatched for current system"""
        
        # Feature extraction
        usage_features = self.extract_usage_features(usage_history)
        performance_features = self.extract_performance_features(performance_history)
        feedback_features = self.extract_feedback_features(neuron_feedback)
        
        # Combined feature vector
        mismatch_features = np.concatenate([
            usage_features,
            performance_features, 
            feedback_features
        ])
        
        # ML model prediction
        mismatch_probability = self.pattern_models['system_mismatch'].predict_proba(
            mismatch_features.reshape(1, -1)
        )[0][1]  # Probability of mismatch class
        
        return mismatch_probability
    
    def detect_consistent_decline(self, usage_history, window=10):
        """Detect consistent decline in usage over recent window"""
        
        if len(usage_history) < window * 2:
            return False
            
        early_period = usage_history[-window*2:-window]
        recent_period = usage_history[-window:]
        
        early_avg = np.mean(early_period)
        recent_avg = np.mean(recent_period)
        
        # Significant decline threshold
        decline_threshold = 0.3
        return (early_avg - recent_avg) > decline_threshold
    
    def detect_never_gained_traction(self, usage_history, threshold=0.2):
        """Detect models that never achieved minimum usage levels"""
        
        if len(usage_history) < 50:  # Need sufficient observation period
            return False
            
        max_usage = np.max(usage_history)
        avg_usage = np.mean(usage_history)
        
        return max_usage < threshold and avg_usage < threshold * 0.5
```

---

## Dynamic Compute Pie Distribution

### Usage-Based Resource Allocation

```python
class DynamicComputePieManager:
    def __init__(self, total_compute_resources=100.0):
        self.total_resources = total_compute_resources
        self.model_allocations = {}
        self.model_usage_trackers = {}
        self.allocation_history = []
        
    def redistribute_compute_pie(self):
        """Redistribute compute resources based on model usage patterns"""
        
        # Collect usage data from all models
        model_usage_scores = {}
        
        for model_id, tracker in self.model_usage_trackers.items():
            usage_score = self.calculate_usage_score(tracker)
            model_usage_scores[model_id] = usage_score
        
        # Calculate new allocations
        total_usage_score = sum(model_usage_scores.values())
        
        if total_usage_score == 0:
            # Equal allocation if no usage data
            equal_share = self.total_resources / len(model_usage_scores)
            new_allocations = {model_id: equal_share for model_id in model_usage_scores}
        else:
            # Proportional allocation based on usage
            new_allocations = {}
            for model_id, usage_score in model_usage_scores.items():
                proportion = usage_score / total_usage_score
                base_allocation = proportion * self.total_resources
                
                # Ensure minimum allocation for all models
                min_allocation = max(1.0, self.total_resources * 0.05)  # 5% minimum
                new_allocations[model_id] = max(min_allocation, base_allocation)
        
        # Normalize to ensure total doesn't exceed available resources
        total_allocated = sum(new_allocations.values())
        if total_allocated > self.total_resources:
            scale_factor = self.total_resources / total_allocated
            new_allocations = {k: v * scale_factor for k, v in new_allocations.items()}
        
        # Update allocations
        self.model_allocations = new_allocations
        self.allocation_history.append({
            'timestamp': time.time(),
            'allocations': new_allocations.copy()
        })
        
        return new_allocations
    
    def calculate_usage_score(self, usage_tracker):
        """Calculate composite usage score for resource allocation"""
        
        usage_rate = usage_tracker.get_recent_usage_rate()
        performance_trend = usage_tracker.get_performance_trend_multiplier()
        efficiency_score = usage_tracker.get_efficiency_score()
        
        # Composite score with weights
        usage_score = (
            usage_rate * 0.5 +           # 50% weight on actual usage
            performance_trend * 0.3 +    # 30% weight on performance trend
            efficiency_score * 0.2       # 20% weight on efficiency
        )
        
        return max(0.1, usage_score)  # Minimum score to prevent zero allocation
    
    def handle_model_stopping(self, model_id):
        """Redistribute resources when a model stops"""
        
        if model_id in self.model_allocations:
            freed_resources = self.model_allocations[model_id]
            del self.model_allocations[model_id]
            
            # Redistribute freed resources among remaining models
            if self.model_allocations:
                bonus_per_model = freed_resources / len(self.model_allocations)
                for remaining_model_id in self.model_allocations:
                    self.model_allocations[remaining_model_id] += bonus_per_model
            
            return freed_resources
        
        return 0.0
```

---

## Integration with Firefly Neural Democracy

### Complete Adaptive System

```python
class AdaptiveFireflyEcosystem:
    def __init__(self):
        self.compute_pie_manager = DynamicComputePieManager()
        self.active_models = {}
        self.stopping_models = {}
        
    def ecosystem_management_loop(self):
        """Main ecosystem management with adaptive controls"""
        
        while True:
            # 1. Let each model run its independent iteration loop
            # (Models run in separate threads/processes)
            
            # 2. Collect usage data from all models
            self.collect_usage_data()
            
            # 3. Redistribute compute pie based on usage patterns
            new_allocations = self.compute_pie_manager.redistribute_compute_pie()
            
            # 4. Apply new allocations to models
            self.apply_compute_allocations(new_allocations)
            
            # 5. Check for models that should stop
            stopping_models = self.identify_stopping_models()
            
            # 6. Handle model stopping and resource reallocation
            for model_id in stopping_models:
                self.gracefully_stop_model(model_id)
            
            # 7. Consider spawning new model types if gaps identified
            self.consider_spawning_new_models()
            
            # Sleep before next ecosystem management cycle
            time.sleep(30)  # 30-second ecosystem management cycle
    
    def gracefully_stop_model(self, model_id):
        """Gracefully stop underperforming model and redistribute resources"""
        
        print(f"Stopping model {model_id} due to ML-recognized stopping pattern")
        
        # 1. Signal model to stop
        self.active_models[model_id].signal_stop()
        
        # 2. Redistribute freed resources
        freed_resources = self.compute_pie_manager.handle_model_stopping(model_id)
        
        # 3. Move to stopping models list for monitoring
        self.stopping_models[model_id] = {
            'stop_time': time.time(),
            'final_usage_score': self.active_models[model_id].get_final_usage_score(),
            'stop_reason': self.active_models[model_id].get_stop_reason()
        }
        
        # 4. Remove from active models
        del self.active_models[model_id]
        
        print(f"Model {model_id} stopped. Redistributed {freed_resources:.2f} compute units to remaining models")

---

## The Jesus Function: Resurrection Through Random Rollback

### Concept: Second Chances Through Historical States

The "Jesus Function" provides redemption for models that may have been prematurely stopped due to temporary bad luck or transient conditions. It randomly resurrects stopped models by rolling back their parameters to earlier, potentially more promising states.

```python
class JesusFunction:
    def __init__(self, resurrection_probability=0.05, max_resurrections_per_model=3):
        self.resurrection_prob = resurrection_probability
        self.max_resurrections = max_resurrections_per_model
        self.model_snapshots = {}  # Historical parameter states
        self.resurrection_history = {}
        self.random_generator = random.Random()
        
    def save_model_snapshot(self, model_id, parameters, performance_metrics, timestamp):
        """Save historical snapshots for potential resurrection"""
        
        if model_id not in self.model_snapshots:
            self.model_snapshots[model_id] = []
            
        snapshot = {
            'parameters': copy.deepcopy(parameters),
            'performance': performance_metrics,
            'timestamp': timestamp,
            'iteration_count': len(self.model_snapshots[model_id])
        }
        
        self.model_snapshots[model_id].append(snapshot)
        
        # Keep only last 50 snapshots to manage memory
        if len(self.model_snapshots[model_id]) > 50:
            self.model_snapshots[model_id] = self.model_snapshots[model_id][-50:]
    
    def consider_resurrection(self, stopped_models):
        """Randomly consider resurrecting stopped models with decay probability"""
        
        resurrection_candidates = []
        
        for model_id, stop_info in stopped_models.items():
            # Check resurrection eligibility
            resurrection_count = self.resurrection_history.get(model_id, 0)
            time_since_stop = time.time() - stop_info['stop_time']
            
            if (resurrection_count < self.max_resurrections and 
                time_since_stop > 300 and  # Wait at least 5 minutes
                model_id in self.model_snapshots and
                len(self.model_snapshots[model_id]) > 5):  # Need some history
                
                # Calculate decay probability based on time since stopping
                base_prob = self.resurrection_prob
                
                # Exponential decay: older stops less likely to resurrect
                days_since_stop = time_since_stop / (24 * 3600)  # Convert to days
                decay_factor = math.exp(-0.5 * days_since_stop)  # Halves every ~1.4 days
                
                # Additional decay based on resurrection count
                resurrection_penalty = 0.7 ** resurrection_count  # Each resurrection 30% less likely
                
                final_probability = base_prob * decay_factor * resurrection_penalty
                
                resurrection_candidates.append((model_id, final_probability))
        
        # Randomly select models for resurrection with individual probabilities
        resurrected_models = []
        
        for model_id, resurrection_prob in resurrection_candidates:
            if self.random_generator.random() < resurrection_prob:
                resurrected_model = self.resurrect_model(model_id, stopped_models[model_id], resurrection_prob)
                if resurrected_model:
                    resurrected_models.append(resurrected_model)
        
        return resurrected_models
    
    def resurrect_model(self, model_id, stop_info, resurrection_probability):
        """Resurrect model from random historical snapshot with distance-based probability"""
        
        snapshots = self.model_snapshots[model_id]
        
        if len(snapshots) < 3:
            return None  # Need sufficient history
            
        # Choose resurrection strategy randomly
        resurrection_strategies = [
            'peak_performance',    # Best performing snapshot
            'random_rollback',     # Random historical state
            'early_promise',       # Early state that showed promise
            'recent_good',         # Most recent good performance
            'mutation_rollback'    # Random state with slight mutations
        ]
        
        strategy = self.random_generator.choice(resurrection_strategies)
        snapshot = self.select_resurrection_snapshot(snapshots, strategy)
        
        if not snapshot:
            return None
            
        # Create resurrected model
        resurrected_model = self.create_resurrected_model(model_id, snapshot, strategy)
        
        # Track resurrection
        self.resurrection_history[model_id] = self.resurrection_history.get(model_id, 0) + 1
        
        print(f"🙏 JESUS FUNCTION: Resurrected {model_id} using {strategy} strategy from iteration {snapshot['iteration_count']}")
        
        return resurrected_model
    
    def select_resurrection_snapshot(self, snapshots, strategy):
        """Select snapshot based on resurrection strategy with distance-based probability"""
        
        # Calculate distance-based weights for all snapshots
        snapshot_weights = self.calculate_distance_weights(snapshots)
        
        if strategy == 'peak_performance':
            # Find snapshot with best performance, weighted by recency
            performance_scores = []
            for i, snapshot in enumerate(snapshots):
                performance = snapshot['performance'].get('efficiency_score', 0)
                distance_weight = snapshot_weights[i]
                weighted_score = performance * (0.7 + 0.3 * distance_weight)  # Bias toward recent good performance
                performance_scores.append(weighted_score)
            
            best_idx = max(range(len(performance_scores)), key=lambda i: performance_scores[i])
            return snapshots[best_idx]
            
        elif strategy == 'random_rollback':
            # Weighted random selection - recent snapshots more likely
            return self.weighted_random_choice(snapshots, snapshot_weights)
            
        elif strategy == 'early_promise':
            # Early snapshot that showed improvement, but still distance-weighted
            early_snapshots = snapshots[:min(15, len(snapshots)//3)]
            early_weights = snapshot_weights[:len(early_snapshots)]
            
            promising_snapshots = []
            promising_weights = []
            
            for i, snapshot in enumerate(early_snapshots):
                if snapshot['performance'].get('trend', '') == 'improving':
                    promising_snapshots.append(snapshot)
                    promising_weights.append(early_weights[i])
            
            if promising_snapshots:
                return self.weighted_random_choice(promising_snapshots, promising_weights)
            return self.weighted_random_choice(early_snapshots, early_weights)
            
        elif strategy == 'recent_good':
            # Recent snapshot with decent performance - naturally favored by distance weighting
            recent_snapshots = snapshots[-min(10, len(snapshots)//3):]
            recent_weights = snapshot_weights[-len(recent_snapshots):]
            
            good_snapshots = []
            good_weights = []
            
            for i, snapshot in enumerate(recent_snapshots):
                if snapshot['performance'].get('efficiency_score', 0) > 0.3:
                    good_snapshots.append(snapshot)
                    good_weights.append(recent_weights[i])
            
            if good_snapshots:
                return self.weighted_random_choice(good_snapshots, good_weights)
            return self.weighted_random_choice(recent_snapshots, recent_weights)
            
        elif strategy == 'mutation_rollback':
            # Weighted random snapshot with parameter mutations
            base_snapshot = self.weighted_random_choice(snapshots, snapshot_weights)
            mutated_snapshot = self.mutate_snapshot_parameters(base_snapshot)
            return mutated_snapshot
            
        return None
    
    def calculate_distance_weights(self, snapshots):
        """Calculate probability weights based on historical distance - recent snapshots more likely"""
        
        num_snapshots = len(snapshots)
        weights = []
        
        for i, snapshot in enumerate(snapshots):
            # Distance from most recent (index 0 = oldest, index -1 = newest)
            distance_from_recent = num_snapshots - 1 - i
            
            # Exponential decay: older snapshots much less likely
            # Recent snapshots get weight ~1.0, older snapshots decay exponentially
            weight = math.exp(-0.3 * distance_from_recent)  # Decay factor
            weights.append(weight)
        
        return weights
    
    def weighted_random_choice(self, items, weights):
        """Choose random item based on weights"""
        
        if not items or not weights:
            return None
            
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return self.random_generator.choice(items)
            
        normalized_weights = [w / total_weight for w in weights]
        
        # Random selection
        r = self.random_generator.random()
        cumsum = 0
        
        for i, weight in enumerate(normalized_weights):
            cumsum += weight
            if r <= cumsum:
                return items[i]
                
        # Fallback to last item
        return items[-1]

---

## ML-Monitored Jesus Function Decay Rate Adjustment

### Neuron-Specific Resurrection Parameters

Each neuron's JSON now contains ML-monitored Jesus function parameters that adapt based on local resurrection success patterns:

```json
{
  "neuron_id": "math_calc_b7k",
  "overall_probability": 0.75,
  "tensor_position": [2, 1, 3, 0, 1, 2],
  "model_affinities": {
    "explorer_firefly": 0.2,
    "specialist_firefly": 0.9
  },
  "jesus_function_params": {
    "base_resurrection_probability": 0.05,
    "time_decay_factor": 0.5,
    "distance_decay_factor": 0.3,
    "resurrection_penalty": 0.7,
    "success_rate_threshold": 0.6,
    "last_ml_adjustment": "2025-01-15T10:30:00Z",
    "adjustment_history": [
      {"date": "2025-01-14", "old_decay": 0.4, "new_decay": 0.5, "reason": "high_success_rate"},
      {"date": "2025-01-10", "old_decay": 0.6, "new_decay": 0.4, "reason": "low_resurrection_efficiency"}
    ]
  }
}
```

### ML-Based Parameter Adjustment System

```python
class AdaptiveJesusParameterManager:
    def __init__(self):
        self.ml_model = JesusDecayOptimizationModel()
        self.adjustment_history = {}
        self.performance_tracker = ResurrectionPerformanceTracker()
        
    def analyze_and_adjust_jesus_parameters(self, neuron_network):
        """ML-based adjustment of Jesus function parameters per neuron"""
        
        for neuron in neuron_network.neurons:
            neuron_id = neuron['neuron_id']
            
            # Gather resurrection performance data for this neuron's models
            local_resurrection_data = self.gather_local_resurrection_data(neuron_id)
            
            if len(local_resurrection_data) >= 10:  # Need sufficient data
                # Analyze current parameter effectiveness
                current_params = neuron.get('jesus_function_params', self.get_default_params())
                performance_metrics = self.calculate_performance_metrics(local_resurrection_data)
                
                # ML prediction for optimal parameters
                optimal_params = self.ml_model.predict_optimal_parameters(
                    current_params=current_params,
                    performance_data=performance_metrics,
                    neuron_context=self.extract_neuron_context(neuron)
                )
                
                # Apply adjustments if improvement expected
                if self.should_adjust_parameters(current_params, optimal_params, performance_metrics):
                    self.apply_parameter_adjustments(neuron, optimal_params, current_params)
    
    def gather_local_resurrection_data(self, neuron_id):
        """Collect resurrection attempts and outcomes for models near this neuron"""
        
        # Find all resurrections within 3-degree radius of this neuron
        local_resurrections = []
        
        for resurrection_event in self.performance_tracker.get_all_resurrections():
            if self.calculate_neuron_distance(neuron_id, resurrection_event['affected_neuron']) <= 3:
                local_resurrections.append(resurrection_event)
        
        return local_resurrections
    
    def calculate_performance_metrics(self, resurrection_data):
        """Calculate effectiveness metrics for current Jesus function parameters"""
        
        if not resurrection_data:
            return {}
            
        # Success rate by decay parameters
        success_by_time_since_death = {}
        success_by_historical_distance = {}
        
        for event in resurrection_data:
            time_category = self.categorize_time_since_death(event['time_since_death'])
            distance_category = self.categorize_historical_distance(event['snapshot_distance'])
            
            # Track success rates
            if time_category not in success_by_time_since_death:
                success_by_time_since_death[time_category] = {'attempts': 0, 'successes': 0}
            if distance_category not in success_by_historical_distance:
                success_by_historical_distance[distance_category] = {'attempts': 0, 'successes': 0}
            
            success_by_time_since_death[time_category]['attempts'] += 1
            success_by_historical_distance[distance_category]['attempts'] += 1
            
            if event['success']:
                success_by_time_since_death[time_category]['successes'] += 1
                success_by_historical_distance[distance_category]['successes'] += 1
        
        return {
            'success_by_time': success_by_time_since_death,
            'success_by_distance': success_by_historical_distance,
            'overall_success_rate': sum(1 for e in resurrection_data if e['success']) / len(resurrection_data),
            'avg_time_to_success': self.calculate_avg_time_to_success(resurrection_data)
        }
    
    def predict_optimal_parameters(self, current_params, performance_data, neuron_context):
        """Use ML to predict optimal Jesus function parameters"""
        
        # Feature engineering
        features = []
        
        # Current parameter features
        features.extend([
            current_params['time_decay_factor'],
            current_params['distance_decay_factor'],  
            current_params['resurrection_penalty'],
            current_params['base_resurrection_probability']
        ])
        
        # Performance features
        features.extend([
            performance_data.get('overall_success_rate', 0),
            performance_data.get('avg_time_to_success', 0),
            len(performance_data.get('success_by_time', {})),
            len(performance_data.get('success_by_distance', {}))
        ])
        
        # Neuron context features
        features.extend([
            neuron_context['activation_probability'],
            neuron_context['connection_count'],
            neuron_context['tensor_position_complexity'],
            neuron_context['model_diversity_score']
        ])
        
        # ML prediction
        feature_vector = np.array(features).reshape(1, -1)
        predicted_params = self.ml_model.predict(feature_vector)[0]
        
        return {
            'time_decay_factor': max(0.1, min(1.0, predicted_params[0])),
            'distance_decay_factor': max(0.1, min(1.0, predicted_params[1])),
            'resurrection_penalty': max(0.3, min(0.9, predicted_params[2])),
            'base_resurrection_probability': max(0.01, min(0.2, predicted_params[3]))
        }
    
    def should_adjust_parameters(self, current_params, optimal_params, performance_metrics):
        """Decide whether to adjust parameters based on expected improvement"""
        
        current_success_rate = performance_metrics.get('overall_success_rate', 0)
        
        # Only adjust if:
        # 1. Current success rate is below threshold, OR
        # 2. Predicted improvement is significant, OR  
        # 3. Parameters haven't been adjusted recently
        
        significant_change = any(
            abs(optimal_params[key] - current_params.get(key, 0)) > 0.15
            for key in optimal_params.keys()
        )
        
        return (current_success_rate < 0.4 or  # Poor performance
                significant_change or          # Big predicted improvement
                self.time_since_last_adjustment(current_params) > 7)  # Weekly adjustments
    
    def apply_parameter_adjustments(self, neuron, optimal_params, current_params):
        """Update neuron's Jesus function parameters"""
        
        # Create adjustment record
        adjustment_record = {
            'date': datetime.now().isoformat(),
            'old_time_decay': current_params.get('time_decay_factor', 0.5),
            'new_time_decay': optimal_params['time_decay_factor'],
            'old_distance_decay': current_params.get('distance_decay_factor', 0.3),
            'new_distance_decay': optimal_params['distance_decay_factor'],
            'reason': self.determine_adjustment_reason(current_params, optimal_params)
        }
        
        # Update neuron parameters
        if 'jesus_function_params' not in neuron:
            neuron['jesus_function_params'] = self.get_default_params()
            
        neuron['jesus_function_params'].update(optimal_params)
        neuron['jesus_function_params']['last_ml_adjustment'] = datetime.now().isoformat()
        
        # Add to history
        if 'adjustment_history' not in neuron['jesus_function_params']:
            neuron['jesus_function_params']['adjustment_history'] = []
            
        neuron['jesus_function_params']['adjustment_history'].append(adjustment_record)
        
        # Keep only last 20 adjustments
        if len(neuron['jesus_function_params']['adjustment_history']) > 20:
            neuron['jesus_function_params']['adjustment_history'] = \
                neuron['jesus_function_params']['adjustment_history'][-20:]
        
        print(f"🎛️  ML-ADJUSTED Jesus parameters for {neuron['neuron_id']}")
        print(f"   Time decay: {current_params.get('time_decay_factor', 0.5):.3f} → {optimal_params['time_decay_factor']:.3f}")
        print(f"   Distance decay: {current_params.get('distance_decay_factor', 0.3):.3f} → {optimal_params['distance_decay_factor']:.3f}")
        print(f"   Reason: {adjustment_record['reason']}")

class NeuronAwareJesusFunction(JesusFunction):
    def __init__(self, neuron_network):
        super().__init__()
        self.neuron_network = neuron_network
        self.parameter_manager = AdaptiveJesusParameterManager()
        
    def get_neuron_specific_parameters(self, model_id):
        """Get Jesus function parameters from the neuron most associated with this model"""
        
        # Find primary neuron for this model (highest affinity)
        primary_neuron = None
        max_affinity = 0
        
        for neuron in self.neuron_network.neurons:
            model_affinity = neuron.get('model_affinities', {}).get(model_id, 0)
            if model_affinity > max_affinity:
                max_affinity = model_affinity
                primary_neuron = neuron
        
        if primary_neuron and 'jesus_function_params' in primary_neuron:
            return primary_neuron['jesus_function_params']
        
        return self.get_default_params()
    
    def consider_resurrection_with_neuron_params(self, stopped_models):
        """Enhanced resurrection with neuron-specific parameters"""
        
        # First, run ML parameter adjustment cycle
        self.parameter_manager.analyze_and_adjust_jesus_parameters(self.neuron_network)
        
        resurrection_candidates = []
        
        for model_id, stop_info in stopped_models.items():
            # Get neuron-specific parameters for this model
            jesus_params = self.get_neuron_specific_parameters(model_id)
            
            resurrection_count = self.resurrection_history.get(model_id, 0)
            time_since_stop = time.time() - stop_info['stop_time']
            
            if (resurrection_count < self.max_resurrections and 
                time_since_stop > 300 and
                model_id in self.model_snapshots and
                len(self.model_snapshots[model_id]) > 5):
                
                # Use ML-learned patterns instead of assumed decay
                base_prob = jesus_params['base_resurrection_probability']
                
                # Let ML determine the actual patterns rather than assuming decay
                ml_probability_adjustment = self.parameter_manager.calculate_ml_probability_adjustment(
                    model_id=model_id,
                    time_since_stop=time_since_stop,
                    resurrection_count=resurrection_count,
                    neuron_context=jesus_params
                )
                
                final_probability = base_prob * ml_probability_adjustment
                
                resurrection_candidates.append((model_id, final_probability, jesus_params))
        
        # Resurrect with neuron-specific parameters
        resurrected_models = []
        
        for model_id, resurrection_prob, jesus_params in resurrection_candidates:
            if self.random_generator.random() < resurrection_prob:
                resurrected_model = self.resurrect_model_with_params(
                    model_id, stopped_models[model_id], jesus_params
                )
                if resurrected_model:
                    resurrected_models.append(resurrected_model)
        
        return resurrected_models
    
    def calculate_ml_probability_adjustment(self, model_id, time_since_stop, resurrection_count, neuron_context):
        """ML-driven probability calculation - may discover patterns opposite to human assumptions"""
        
        # Gather historical data for similar situations
        similar_cases = self.find_similar_resurrection_cases(
            model_id, time_since_stop, resurrection_count
        )
        
        if len(similar_cases) < 5:
            # Not enough data - use neutral adjustment
            return 1.0
        
        # Extract features for ML prediction
        features = self.extract_resurrection_features(
            time_since_stop, resurrection_count, similar_cases, neuron_context
        )
        
        # ML prediction of success probability given these conditions
        predicted_success_probability = self.ml_model.predict_resurrection_success_probability(features)
        
        # Convert success probability to resurrection attempt probability
        # Higher success chance may justify higher attempt probability
        if predicted_success_probability > 0.6:
            # High success chance - INCREASE resurrection attempts
            adjustment_factor = 1.0 + (predicted_success_probability - 0.6) * 2.0  # Up to 1.8x
        elif predicted_success_probability > 0.3:
            # Moderate success chance - normal attempts
            adjustment_factor = 0.8 + (predicted_success_probability * 0.67)  # 0.8 to 1.2x  
        else:
            # Low success chance - reduce attempts
            adjustment_factor = predicted_success_probability * 2.0  # Up to 0.6x
        
        return max(0.1, min(3.0, adjustment_factor))  # Bounded between 0.1x and 3.0x

    def mutate_snapshot_parameters(self, snapshot, mutation_rate=0.1):
        """Create mutated version of snapshot parameters"""
        
        mutated_snapshot = copy.deepcopy(snapshot)
        parameters = mutated_snapshot['parameters']
        
        # Apply random mutations to parameters
        for key, value in parameters.items():
            if isinstance(value, (int, float)) and self.random_generator.random() < mutation_rate:
                if isinstance(value, float):
                    # Add gaussian noise
                    mutation = self.random_generator.gauss(0, abs(value) * 0.1)
                    parameters[key] = max(0.0, min(1.0, value + mutation))
                elif isinstance(value, int):
                    # Small integer mutation
                    mutation = self.random_generator.choice([-1, 0, 1])
                    parameters[key] = max(0, value + mutation)
        
        mutated_snapshot['resurrection_type'] = 'mutated'
        return mutated_snapshot
    
    def create_resurrected_model(self, original_model_id, snapshot, strategy):
        """Create new model instance from resurrection snapshot"""
        
        # Generate resurrection ID
        resurrection_count = self.resurrection_history.get(original_model_id, 0) + 1
        resurrected_id = f"{original_model_id}_resurrection_{resurrection_count}"
        
        # Create new model with historical parameters
        resurrected_model = IndependentFireflyModel(
            model_id=resurrected_id,
            model_type=f"resurrected_{original_model_id.split('_')[0]}"
        )
        
        # Load historical parameters
        resurrected_model.load_parameters(snapshot['parameters'])
        
        # Set resurrection metadata
        resurrected_model.resurrection_info = {
            'original_id': original_model_id,
            'resurrection_strategy': strategy,
            'source_iteration': snapshot['iteration_count'],
            'source_timestamp': snapshot['timestamp'],
            'resurrection_time': time.time(),
            'resurrection_number': resurrection_count
        }
        
        # Give resurrection bonus - slightly higher initial compute allocation
        resurrection_bonus = 1.2  # 20% bonus compute to give second chance
        resurrected_model.compute_allocator.set_initial_allocation(
            resurrected_model.compute_allocator.base_allocation * resurrection_bonus
        )
        
        return resurrected_model

class AdaptiveFireflyEcosystemWithResurrection(AdaptiveFireflyEcosystem):
    def __init__(self):
        super().__init__()
        self.jesus_function = JesusFunction()
        self.resurrection_monitor = ResurrectionPerformanceMonitor()
        
    def ecosystem_management_loop(self):
        """Enhanced ecosystem management with resurrection capability"""
        
        while True:
            # Standard ecosystem management
            self.collect_usage_data()
            new_allocations = self.compute_pie_manager.redistribute_compute_pie()
            self.apply_compute_allocations(new_allocations)
            
            # Save snapshots for potential resurrection
            self.save_model_snapshots()
            
            # Handle model stopping
            stopping_models = self.identify_stopping_models()
            for model_id in stopping_models:
                self.gracefully_stop_model(model_id)
            
            # 🙏 JESUS FUNCTION: Consider resurrections
            resurrected_models = self.jesus_function.consider_resurrection(self.stopping_models)
            
            for resurrected_model in resurrected_models:
                self.integrate_resurrected_model(resurrected_model)
            
            # Monitor resurrection performance
            self.monitor_resurrection_success()
            
            time.sleep(30)  # Standard ecosystem cycle
    
    def save_model_snapshots(self):
        """Save current state snapshots for all active models"""
        
        current_time = time.time()
        
        for model_id, model in self.active_models.items():
            parameters = model.get_current_parameters()
            performance = model.get_performance_metrics()
            
            self.jesus_function.save_model_snapshot(
                model_id, parameters, performance, current_time
            )
    
    def integrate_resurrected_model(self, resurrected_model):
        """Integrate resurrected model back into active ecosystem"""
        
        # Add to active models
        self.active_models[resurrected_model.model_id] = resurrected_model
        
        # Allocate initial compute resources  
        self.compute_pie_manager.add_new_model(
            resurrected_model.model_id, 
            resurrected_model.get_initial_compute_allocation()
        )
        
        # Start its independent iteration loop
        resurrected_model.start_autonomous_loop()
        
        original_id = resurrected_model.resurrection_info['original_id']
        strategy = resurrected_model.resurrection_info['resurrection_strategy']
        
        print(f"✨ Resurrected model {resurrected_model.model_id} integrated into ecosystem")
        print(f"   Original: {original_id}, Strategy: {strategy}")
    
    def monitor_resurrection_success(self):
        """Track whether resurrections are working"""
        
        for model_id, model in self.active_models.items():
            if hasattr(model, 'resurrection_info'):
                # This is a resurrected model - monitor its performance
                time_since_resurrection = time.time() - model.resurrection_info['resurrection_time']
                
                if time_since_resurrection > 1800:  # 30 minutes
                    success = self.evaluate_resurrection_success(model)
                    
                    self.resurrection_monitor.record_resurrection_outcome(
                        model.resurrection_info,
                        success
                    )
                    
                    if success:
                        print(f"🎉 Resurrection SUCCESS: {model_id} performing well after resurrection!")
                    else:
                        print(f"💀 Resurrection failed: {model_id} still underperforming despite second chance")
    
    def evaluate_resurrection_success(self, resurrected_model):
        """Determine if resurrection was successful"""
        
        current_performance = resurrected_model.get_performance_metrics()
        usage_rate = resurrected_model.usage_tracker.get_recent_usage_rate()
        
        # Success criteria
        min_usage_rate = 0.3  # At least 30% usage
        min_efficiency = 0.4  # At least 40% efficiency
        
        return (usage_rate >= min_usage_rate and 
                current_performance.get('efficiency_score', 0) >= min_efficiency)

class ResurrectionPerformanceMonitor:
    def __init__(self):
        self.resurrection_outcomes = []
        self.strategy_success_rates = {}
        
    def record_resurrection_outcome(self, resurrection_info, success):
        """Record outcome of a resurrection attempt"""
        
        outcome = {
            'original_id': resurrection_info['original_id'],
            'strategy': resurrection_info['resurrection_strategy'],
            'success': success,
            'evaluation_time': time.time()
        }
        
        self.resurrection_outcomes.append(outcome)
        
        # Update strategy success rates
        strategy = resurrection_info['resurrection_strategy']
        if strategy not in self.strategy_success_rates:
            self.strategy_success_rates[strategy] = {'successes': 0, 'total': 0}
            
        self.strategy_success_rates[strategy]['total'] += 1
        if success:
            self.strategy_success_rates[strategy]['successes'] += 1
    
    def get_best_resurrection_strategies(self):
        """Identify which resurrection strategies work best"""
        
        strategy_rates = {}
        for strategy, stats in self.strategy_success_rates.items():
            if stats['total'] >= 5:  # Need minimum attempts for reliable rate
                strategy_rates[strategy] = stats['successes'] / stats['total']
        
        return sorted(strategy_rates.items(), key=lambda x: x[1], reverse=True)
```
```

This adaptive system creates truly autonomous firefly bot models that:

1. **Self-Regulate**: Control their own iteration speed based on usage
2. **Compete for Resources**: Dynamically request more/less compute based on performance
3. **Recognize Stopping Conditions**: Use ML to identify when they're no longer effective
4. **Gracefully Retire**: Stop themselves when patterns indicate system mismatch

The result is a completely self-organizing ecosystem where successful models naturally get more resources and iteration speed, while unsuccessful models slow down and eventually stop automatically, freeing resources for better-performing alternatives.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Generate white papers and promotional materials at all levels", "status": "completed", "activeForm": "Created executive white paper and adaptive iteration control system"}, {"content": "Add new bot to AI Professor College debates", "status": "in_progress", "activeForm": "Adding Dr. Firefly Neural Democracy Bot to college debates"}]