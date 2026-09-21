# Firefly Bots: ML-Tuned Navigation in Bacon's Law Neural Networks

## Definition: Firefly Bots

**Firefly Bots** are lightweight, scalable models that navigate through tensor-spatial neural networks like fireflies seeking bright lights in the darkness. They move toward neurons with higher "probability of firing" (brighter lights) while machine learning continuously refines and tunes them to different sizes for different computational tasks.

Named for their natural behavior of flying toward bright areas to find their "next thing to do," Firefly Bots eliminate the need for complex cue systems - the brightness itself is the cue. ML algorithms constantly optimize bot size, behavior, and efficiency based on task requirements and network conditions.

---

## Core Concept: Probability as Brightness

### Visual Metaphor
**Probability of Firing = Brightness**: Each JSON neuron's probability value (0-1) is visualized as light intensity:
- **1.0 probability** = Brilliant white light (maximum neural activity)
- **0.5 probability** = Medium brightness (moderate activity)
- **0.0 probability** = Darkness (inactive neuron)

### Firefly Bot Behavior
**Natural Light-Seeking**: Firefly Bots instinctively fly toward brighter neurons, creating emergent patterns of:
- **Information concentration** at high-activity nodes
- **Processing migration** toward active computation  
- **Resource optimization** through brightness-guided movement
- **Adaptive sizing** via ML tuning for optimal task performance

---

## Mathematical Foundation

### Firefly Bot Movement Algorithm with ML Tuning

```python
class FireflyBot:
    def __init__(self, agent_id, current_position, sensing_radius=2, size_class="medium"):
        self.agent_id = agent_id
        self.position = current_position  # Tensor coordinates
        self.sensing_radius = sensing_radius
        self.energy = 1.0
        self.memory_trace = []
        self.size_class = size_class  # "nano", "small", "medium", "large", "giant"
        self.ml_optimizer = MLFireflyOptimizer()
        self.performance_metrics = []
        
    def sense_brightness(self, tensor_network):
        """Detect probability values (brightness) within sensing radius"""
        nearby_neurons = get_neurons_in_radius(
            self.position, self.sensing_radius, tensor_network
        )
        
        brightness_map = {}
        for neuron in nearby_neurons:
            probability = get_neuron_probability(neuron)
            distance = calculate_tensor_distance(self.position, neuron.position)
            
            # Brightness decreases with distance (inverse square law)
            perceived_brightness = probability / (distance ** 2 + 1)
            brightness_map[neuron] = perceived_brightness
            
        return brightness_map
    
    def calculate_attraction_vector(self, brightness_map):
        """Calculate movement vector toward brightest neurons"""
        if not brightness_map:
            return np.zeros(6)  # No movement in 6D tensor space
            
        attraction_vector = np.zeros(6)
        
        for neuron, brightness in brightness_map.items():
            direction = neuron.position - self.position
            direction_normalized = direction / (np.linalg.norm(direction) + 1e-6)
            
            # Attraction strength proportional to brightness
            attraction_strength = brightness * self.energy
            attraction_vector += direction_normalized * attraction_strength
            
        return attraction_vector
    
    def move_toward_brightness(self, tensor_network):
        """Execute one movement step toward brighter neurons"""
        brightness_map = self.sense_brightness(tensor_network)
        attraction_vector = self.calculate_attraction_vector(brightness_map)
        
        # Apply Bacon's Law constraint (max 6-degree movement)
        movement_magnitude = min(np.linalg.norm(attraction_vector), 1.0)
        
        if movement_magnitude > 0:
            new_position = self.position + attraction_vector
            
            # Ensure movement respects Bacon's Law boundaries
            new_position = enforce_bacon_law_bounds(new_position)
            
            # Update position and memory
            self.memory_trace.append(self.position)
            self.position = new_position
            
            # Energy decreases with movement
            self.energy *= 0.98
            
            return True  # Successful movement
        
        return False  # No movement needed
    
    def ml_tune_parameters(self):
        """ML system continuously refines firefly bot parameters"""
        recent_performance = self.performance_metrics[-50:]  # Last 50 iterations
        
        if len(recent_performance) < 10:
            return  # Not enough data for tuning
            
        tuning_result = self.ml_optimizer.optimize_firefly(
            current_params={
                'sensing_radius': self.sensing_radius,
                'energy_decay': 0.98,
                'movement_speed': 1.0,
                'size_class': self.size_class
            },
            performance_history=recent_performance,
            task_requirements=self.get_current_task_requirements()
        )
        
        # Apply ML-suggested improvements
        if tuning_result['improvement_score'] > 0.05:
            self.sensing_radius = tuning_result['new_sensing_radius']
            self.size_class = tuning_result['optimal_size_class']
            self.energy_efficiency = tuning_result['energy_efficiency']
```

### ML-Optimized Firefly Swarm Intelligence

```python
class MLFireflyOptimizer:
    def __init__(self):
        self.size_templates = {
            "nano": {"sensing_radius": 1, "energy_capacity": 0.5, "speed": 1.5},
            "small": {"sensing_radius": 1.5, "energy_capacity": 0.8, "speed": 1.2},
            "medium": {"sensing_radius": 2, "energy_capacity": 1.0, "speed": 1.0},
            "large": {"sensing_radius": 3, "energy_capacity": 1.5, "speed": 0.8},
            "giant": {"sensing_radius": 4, "energy_capacity": 2.0, "speed": 0.6}
        }
        self.ml_model = self.load_pretrained_optimizer_model()
    
    def optimize_firefly(self, current_params, performance_history, task_requirements):
        """Use ML to find optimal firefly bot configuration"""
        
        # Analyze task requirements
        task_complexity = self.analyze_task_complexity(task_requirements)
        network_density = self.calculate_network_density(task_requirements)
        brightness_distribution = self.analyze_brightness_patterns(task_requirements)
        
        # ML prediction for optimal size class
        features = np.array([
            task_complexity,
            network_density, 
            brightness_distribution['variance'],
            np.mean(performance_history),
            len(performance_history)
        ]).reshape(1, -1)
        
        optimal_size_prediction = self.ml_model.predict(features)[0]
        optimal_size_class = self.map_prediction_to_size_class(optimal_size_prediction)
        
        return {
            'optimal_size_class': optimal_size_class,
            'new_sensing_radius': self.size_templates[optimal_size_class]['sensing_radius'],
            'energy_efficiency': self.size_templates[optimal_size_class]['energy_capacity'],
            'improvement_score': self.calculate_improvement_score(current_params, optimal_size_class),
            'recommended_compute_allocation': self.calculate_compute_needs(optimal_size_class),
            'parallel_instances_suggested': self.suggest_parallel_instances(task_requirements)
        }

class FireflySwarm:
    def __init__(self, num_agents, tensor_network):
        self.ml_optimizer = MLFireflyOptimizer()
        self.agents = [
            FireflyBot(f"firefly_{i}", random_tensor_position(), size_class=self.ml_optimizer.select_initial_size()) 
            for i in range(num_agents)
        ]
        self.tensor_network = tensor_network
        self.iteration_count = 0
        
    def swarm_iteration(self):
        """Execute one iteration of swarm movement"""
        movements = []
        
        for agent in self.agents:
            moved = agent.move_toward_brightness(self.tensor_network)
            movements.append(moved)
            
        # Collective behavior effects
        self.apply_swarm_interactions()
        self.spawn_new_agents_if_needed()
        self.remove_depleted_agents()
        
        self.iteration_count += 1
        
        return {
            "active_agents": len(self.agents),
            "movements_made": sum(movements),
            "average_energy": np.mean([a.energy for a in self.agents]),
            "brightest_neuron": self.find_brightest_neuron()
        }
    
    def apply_swarm_interactions(self):
        """Agents influence each other's behavior"""
        for i, agent1 in enumerate(self.agents):
            for j, agent2 in enumerate(self.agents[i+1:], i+1):
                distance = calculate_tensor_distance(agent1.position, agent2.position)
                
                if distance < 0.5:  # Close proximity
                    # Share information about bright areas
                    shared_memory = agent1.memory_trace + agent2.memory_trace
                    bright_spots = find_brightest_positions(shared_memory)
                    
                    # Both agents gain knowledge of bright areas
                    agent1.shared_brightness_knowledge = bright_spots
                    agent2.shared_brightness_knowledge = bright_spots
```

---

## Dynamic Resource Allocation Based on Performance

### Compute Delegation System

**Performance-Based Resource Allocation**: Different firefly bot models receive more or less computational resources based on their results and effectiveness in finding bright neurons.

```python
class ComputeResourceManager:
    def __init__(self):
        self.resource_pool = 100.0  # Total available compute units
        self.allocation_history = {}
        self.performance_tracker = {}
        
    def delegate_compute_resources(self, firefly_swarm):
        """Allocate compute resources based on firefly bot performance"""
        
        # Evaluate each firefly's recent performance
        performance_scores = {}
        for firefly in firefly_swarm.agents:
            recent_brightness_found = sum(firefly.brightness_discoveries[-20:])  # Last 20 iterations
            efficiency_score = recent_brightness_found / firefly.energy_consumed
            movement_efficiency = firefly.successful_movements / firefly.total_movements
            
            performance_scores[firefly.agent_id] = {
                'brightness_score': recent_brightness_found,
                'efficiency_score': efficiency_score,
                'movement_score': movement_efficiency,
                'composite_score': (recent_brightness_found * 0.4 + 
                                  efficiency_score * 0.4 + 
                                  movement_efficiency * 0.2)
            }
        
        # Rank fireflies by performance
        ranked_fireflies = sorted(
            performance_scores.items(), 
            key=lambda x: x[1]['composite_score'], 
            reverse=True
        )
        
        # Allocate resources proportionally
        total_performance = sum(score['composite_score'] for _, score in ranked_fireflies)
        
        resource_allocations = {}
        for firefly_id, score in ranked_fireflies:
            if total_performance > 0:
                allocation_ratio = score['composite_score'] / total_performance
                compute_units = self.resource_pool * allocation_ratio
                resource_allocations[firefly_id] = {
                    'compute_units': compute_units,
                    'priority_level': self.calculate_priority_level(compute_units),
                    'parallel_instances': self.calculate_parallel_instances(compute_units)
                }
        
        return resource_allocations
    
    def calculate_parallel_instances(self, compute_allocation):
        """Determine how many parallel instances to spawn based on compute allocation"""
        if compute_allocation > 20:
            return min(8, int(compute_allocation / 5))  # Up to 8 parallel instances
        elif compute_allocation > 10:
            return min(4, int(compute_allocation / 3))  # Up to 4 parallel instances
        elif compute_allocation > 5:
            return min(2, int(compute_allocation / 2.5))  # Up to 2 parallel instances
        else:
            return 1  # Single instance for low performers
```

### Parallel Instance Management

```python
class ParallelFireflyManager:
    def __init__(self, base_firefly_bot, num_instances=1):
        self.base_bot = base_firefly_bot
        self.instances = []
        self.results_aggregator = ResultsAggregator()
        self.spawn_parallel_instances(num_instances)
    
    def spawn_parallel_instances(self, num_instances):
        """Create multiple parallel instances of high-performing fireflies"""
        self.instances = []
        
        for i in range(num_instances):
            # Clone the base firefly with slight variations
            instance = FireflyBot(
                agent_id=f"{self.base_bot.agent_id}_parallel_{i}",
                current_position=self.add_position_noise(self.base_bot.position),
                sensing_radius=self.base_bot.sensing_radius,
                size_class=self.base_bot.size_class
            )
            
            # Share learned knowledge with parallel instance
            instance.shared_brightness_knowledge = self.base_bot.shared_brightness_knowledge
            instance.memory_trace = self.base_bot.memory_trace.copy()
            
            self.instances.append(instance)
    
    def coordinate_parallel_exploration(self, tensor_network):
        """Coordinate multiple instances to explore different areas"""
        exploration_results = []
        
        # Divide search space among instances
        search_regions = self.divide_search_space(len(self.instances))
        
        for i, instance in enumerate(self.instances):
            # Assign search region to instance
            instance.preferred_search_region = search_regions[i]
            
            # Execute parallel exploration
            result = instance.explore_region(tensor_network, search_regions[i])
            exploration_results.append(result)
        
        # Aggregate results from all parallel instances
        aggregated_result = self.results_aggregator.combine_results(exploration_results)
        
        # Share discoveries among all instances
        for instance in self.instances:
            instance.incorporate_shared_discoveries(aggregated_result)
        
        return aggregated_result
    
    def scale_instances_dynamically(self, performance_metrics):
        """Dynamically scale parallel instances based on performance"""
        current_efficiency = performance_metrics['brightness_per_compute_unit']
        
        if current_efficiency > 0.8 and len(self.instances) < 8:
            # High efficiency: spawn more instances
            new_instances_needed = min(2, 8 - len(self.instances))
            self.spawn_additional_instances(new_instances_needed)
            
        elif current_efficiency < 0.3 and len(self.instances) > 1:
            # Low efficiency: reduce instances
            instances_to_remove = max(1, len(self.instances) // 2)
            self.terminate_underperforming_instances(instances_to_remove)
```

### Multi-Model Ecosystem

```python
class MultiModelFireflyEcosystem:
    def __init__(self, tensor_network):
        self.tensor_network = tensor_network
        self.model_types = {
            'explorer': ExplorerFireflyBot,      # High-mobility, wide sensing
            'specialist': SpecialistFireflyBot,  # Deep analysis, narrow focus  
            'coordinator': CoordinatorFireflyBot, # Cross-model communication
            'harvester': HarvesterFireflyBot,    # Efficient brightness collection
            'scout': ScoutFireflyBot            # Long-range pathfinding
        }
        self.active_models = {}
        self.resource_manager = ComputeResourceManager()
        
    def deploy_model_mix(self, task_requirements):
        """Deploy optimal mix of different firefly models for task"""
        
        # Analyze task to determine optimal model composition
        task_analysis = self.analyze_task_requirements(task_requirements)
        
        model_composition = {
            'explorer': max(1, int(task_analysis['exploration_needs'] * 10)),
            'specialist': max(1, int(task_analysis['deep_analysis_needs'] * 5)),
            'coordinator': max(1, int(task_analysis['coordination_needs'] * 3)),
            'harvester': max(1, int(task_analysis['efficiency_needs'] * 8)),
            'scout': max(1, int(task_analysis['pathfinding_needs'] * 4))
        }
        
        # Deploy models with appropriate resource allocation
        for model_type, count in model_composition.items():
            self.deploy_model_instances(model_type, count, task_requirements)
    
    def deploy_model_instances(self, model_type, count, task_requirements):
        """Deploy specific number of instances for a model type"""
        
        model_class = self.model_types[model_type]
        
        for i in range(count):
            # Create model instance
            instance = model_class(
                agent_id=f"{model_type}_{i}",
                current_position=self.select_optimal_spawn_position(model_type),
                task_specialization=task_requirements
            )
            
            # Allocate initial compute resources
            initial_allocation = self.resource_manager.allocate_initial_resources(
                model_type, task_requirements
            )
            
            instance.set_compute_allocation(initial_allocation)
            
            # Add to active models
            if model_type not in self.active_models:
                self.active_models[model_type] = []
            self.active_models[model_type].append(instance)
    
    def rebalance_ecosystem(self):
        """Continuously rebalance resources based on model performance"""
        
        # Evaluate performance of all model types
        model_performance = {}
        for model_type, instances in self.active_models.items():
            total_brightness_found = sum(inst.total_brightness_discovered for inst in instances)
            total_compute_used = sum(inst.compute_units_consumed for inst in instances)
            
            model_performance[model_type] = {
                'efficiency': total_brightness_found / (total_compute_used + 1e-6),
                'absolute_performance': total_brightness_found,
                'instance_count': len(instances)
            }
        
        # Reallocate resources to high-performing models
        for model_type, performance in model_performance.items():
            if performance['efficiency'] > 0.7:
                # High efficiency: allocate more resources/instances
                self.boost_model_resources(model_type, 1.3)
                
            elif performance['efficiency'] < 0.3:
                # Low efficiency: reduce resources/instances
                self.reduce_model_resources(model_type, 0.7)
```

---

## Integration with Bacon's Law Framework

### Six-Degree Navigation Constraints

**Spark Agent Movement Rules**:
1. Agents can sense brightness within 2 tensor units
2. Movement per iteration limited to 1 tensor unit
3. No agent path can exceed 6 degrees from any neuron
4. Agents automatically route via central hubs when direct paths exceed 6 degrees

```python
def enforce_bacon_law_navigation(agent, target_position):
    """Ensure agent movement respects Bacon's Law constraints"""
    
    # Calculate direct path to target
    direct_path = calculate_tensor_path(agent.position, target_position)
    
    if len(direct_path) <= 6:
        # Direct navigation allowed
        return direct_path[1]  # Next step in path
    
    # Route via central hub for distant targets
    central_hub = find_most_central_neuron(agent.tensor_network)
    hub_path = calculate_tensor_path(agent.position, central_hub.position)
    
    if len(hub_path) > 0:
        return hub_path[1]  # Move toward hub first
    
    return agent.position  # Stay in place if no valid path
```

### Brightness-Driven Network Organization

**Emergent Clustering**: Spark Agents naturally create clusters around high-probability neurons, leading to:
- **Hot zones** of concentrated processing power
- **Information highways** between frequently accessed neurons  
- **Adaptive network topology** based on usage patterns

---

## Bash Communication Integration

### Spark Agent File Operations

```bash
# Spark Agent communication using filename-as-key
spark_agent_communicate() {
    local agent_id="$1"
    local target_neuron="$2"
    local brightness_info="$3"
    
    # Leave brightness report for target neuron
    echo "Brightness: $brightness_info" > ${target_neuron}.spark_report
    echo "Agent: $agent_id" >> ${target_neuron}.spark_report
    echo "Timestamp: $(date)" >> ${target_neuron}.spark_report
    echo "Tensor_position: $(get_agent_position $agent_id)" >> ${target_neuron}.spark_report
}

# Neuron receives brightness reports from Spark Agents
process_spark_reports() {
    local neuron_key="$1"
    
    if [ -f "${neuron_key}.spark_report" ]; then
        brightness_level=$(grep "Brightness:" ${neuron_key}.spark_report | cut -d' ' -f2)
        reporting_agent=$(grep "Agent:" ${neuron_key}.spark_report | cut -d' ' -f2)
        
        # Adjust own probability based on Spark Agent activity
        if [ "$brightness_level" -gt "0.8" ]; then
            # High agent activity suggests this neuron should increase probability
            increase_neuron_probability "$neuron_key" "0.1"
        fi
        
        # Archive processed report
        mv ${neuron_key}.spark_report processed/spark_report_$(date +%s)
    fi
}
```

---

## Advanced Spark Agent Behaviors

### Collaborative Exploration

```python
def collaborative_brightness_mapping(spark_swarm):
    """Agents work together to map brightness across tensor space"""
    
    # Combine all agent observations
    global_brightness_map = {}
    
    for agent in spark_swarm.agents:
        agent_observations = agent.brightness_observations
        
        for position, brightness in agent_observations.items():
            if position not in global_brightness_map:
                global_brightness_map[position] = []
            
            global_brightness_map[position].append(brightness)
    
    # Calculate consensus brightness values
    consensus_map = {}
    for position, brightness_list in global_brightness_map.items():
        consensus_map[position] = np.mean(brightness_list)
    
    # Share consensus with all agents
    for agent in spark_swarm.agents:
        agent.global_brightness_knowledge = consensus_map
    
    return consensus_map
```

### Adaptive Agent Spawning

```python
def adaptive_agent_spawning(tensor_network):
    """Spawn new Spark Agents in areas of high activity"""
    
    # Find neurons with rapidly changing probability
    dynamic_neurons = find_dynamic_neurons(tensor_network)
    
    new_agents = []
    for neuron in dynamic_neurons:
        if neuron.probability > 0.7 and neuron.change_rate > 0.1:
            # Spawn new agent near high-activity neuron
            spawn_position = neuron.position + random_offset(0.5)
            new_agent = SparkAgent(f"spark_adaptive_{len(new_agents)}", spawn_position)
            new_agents.append(new_agent)
    
    return new_agents
```

---

## Visualization Framework

### Brightness Rendering System

```python
def render_spark_agents_visualization(tensor_network, spark_swarm):
    """Generate 3D visualization of Spark Agents and neuron brightness"""
    
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D
    
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plot neurons as spheres with brightness-based color
    for neuron in tensor_network.neurons:
        brightness = neuron.probability
        color_intensity = brightness  # 0-1 scale
        
        ax.scatter(
            neuron.position[0], neuron.position[1], neuron.position[2],
            s=100 * brightness,  # Size proportional to brightness
            c=[[color_intensity, color_intensity, 1.0]],  # Blue to white
            alpha=0.6,
            label=f"Neuron (p={brightness:.2f})"
        )
    
    # Plot Spark Agents as moving points
    for agent in spark_swarm.agents:
        ax.scatter(
            agent.position[0], agent.position[1], agent.position[2],
            s=20,
            c='red',
            marker='^',
            alpha=0.8
        )
        
        # Draw agent trajectory
        if len(agent.memory_trace) > 1:
            trajectory = np.array(agent.memory_trace[-10:])  # Last 10 positions
            ax.plot(
                trajectory[:, 0], trajectory[:, 1], trajectory[:, 2],
                'r--', alpha=0.4, linewidth=1
            )
    
    ax.set_title("Spark Agents Navigating Toward Bright Neurons")
    ax.set_xlabel("Tensor Dimension 1")
    ax.set_ylabel("Tensor Dimension 2") 
    ax.set_zlabel("Tensor Dimension 3")
    
    return fig
```

---

## Public Understanding Benefits

### Intuitive Metaphors

**"Digital Fireflies"**: Firefly Bots behave exactly like real fireflies drawn to bright lights, making neural network dynamics instantly intuitive for anyone.

**"Natural Intelligence"**: Bots instinctively seek brighter areas (higher probability neurons) just like fireflies seek light sources in nature.

**"Adaptive Swarm"**: Multiple fireflies working together naturally optimize the entire network, with ML continuously tuning their behavior and spawning more instances of successful bots.

### Educational Applications

**Interactive Visualization**: Students can watch Firefly Bots swarm in real-time toward brighter neurons, making abstract tensor mathematics as visual and engaging as watching real fireflies.

**Gaming Elements**: Users can guide firefly swarms or compete to find the brightest neural pathways, with ML automatically optimizing bot performance based on player strategies.

---

## Technical Advantages

### Performance Benefits
- **Natural Load Balancing**: Fireflies instinctively distribute toward high-activity areas
- **ML-Optimized Resources**: Computing power automatically concentrates where most effective  
- **Adaptive Fault Tolerance**: Swarms naturally adapt when neurons fail or change
- **Dynamic Scaling**: ML spawns more instances of successful fireflies, terminates inefficient ones

### Scalability Features  
- **Massive Parallelism**: Thousands of firefly bots can swarm simultaneously
- **Decentralized Intelligence**: No central control needed - emergent swarm behavior
- **Performance-Based Scaling**: High-performing models get more compute and parallel instances
- **Multi-Model Ecosystem**: Different firefly types optimized for different tasks

### Research Applications
- **Behavioral Analysis**: Firefly movement patterns reveal optimal network pathways
- **ML-Driven Optimization**: Continuous tuning creates ever-improving swarm intelligence  
- **Emergence Studies**: Simple brightness-seeking rules create sophisticated collective behaviors
- **Resource Efficiency**: Performance-based allocation maximizes computational effectiveness

This Firefly Bots framework transforms complex distributed neural computation into an intuitive, naturally-inspired system where ML continuously optimizes performance while maintaining the visual appeal and accessibility of watching digital fireflies navigate toward bright neural activity.

---

## Neuron-Level Model Selection and Voting

### Per-Neuron Model Probability System

**Enhanced JSON Neuron Structure**: Each neuron maintains separate probability scores for different firefly bot models, creating a distributed democracy where neurons "vote" for which models should process them.

```json
{
  "neuron_id": "math_calc_b7k",
  "overall_probability": 0.75,
  "tensor_position": [2, 1, 3, 0, 1, 2],
  "model_affinities": {
    "explorer_firefly": 0.2,      // Poor performance on this neuron
    "specialist_firefly": 0.9,    // Excellent results - high preference  
    "coordinator_firefly": 0.6,   // Moderate success
    "harvester_firefly": 0.8,     // Good efficiency here
    "scout_firefly": 0.3          // Limited success
  },
  "model_performance_history": {
    "explorer_firefly": {
      "attempts": 45,
      "successes": 12,
      "avg_brightness_found": 0.2,
      "trend": "declining"
    },
    "specialist_firefly": {
      "attempts": 23,
      "successes": 21,
      "avg_brightness_found": 0.85,
      "trend": "improving"
    }
  },
  "vote_weight": 0.75,  // This neuron's voting influence based on importance
  "last_updated": "2025-01-15T10:30:00Z"
}
```

### Neuron-Based Model Selection Algorithm

```python
class NeuronModelSelector:
    def __init__(self, neuron_data):
        self.neuron_data = neuron_data
        self.model_affinities = neuron_data.get('model_affinities', {})
        self.performance_history = neuron_data.get('model_performance_history', {})
        
    def select_optimal_model(self, available_models):
        """Neuron selects which model should process it based on performance history"""
        
        if not self.model_affinities:
            # New neuron - random selection for initial learning
            return random.choice(available_models)
        
        # Weight selection by model performance on this specific neuron
        model_weights = []
        for model in available_models:
            affinity = self.model_affinities.get(model, 0.5)  # Default neutral
            
            # Boost weight for models with improving trends
            trend_bonus = 0
            if model in self.performance_history:
                trend = self.performance_history[model].get('trend', 'stable')
                if trend == 'improving':
                    trend_bonus = 0.2
                elif trend == 'declining':
                    trend_bonus = -0.2
            
            final_weight = max(0.1, affinity + trend_bonus)  # Minimum 10% chance
            model_weights.append(final_weight)
        
        # Probabilistic selection weighted by performance
        selected_model = np.random.choice(
            available_models, 
            p=np.array(model_weights) / sum(model_weights)
        )
        
        return selected_model
    
    def update_model_performance(self, model_type, success, brightness_achieved):
        """Update neuron's opinion of model performance"""
        
        if model_type not in self.performance_history:
            self.performance_history[model_type] = {
                'attempts': 0,
                'successes': 0,
                'brightness_history': [],
                'trend': 'stable'
            }
        
        history = self.performance_history[model_type]
        history['attempts'] += 1
        
        if success:
            history['successes'] += 1
        
        history['brightness_history'].append(brightness_achieved)
        
        # Calculate new affinity based on recent performance
        recent_performance = history['brightness_history'][-10:]  # Last 10 attempts
        success_rate = history['successes'] / history['attempts']
        avg_brightness = np.mean(recent_performance) if recent_performance else 0
        
        # Update affinity: 60% success rate, 40% brightness quality
        new_affinity = (success_rate * 0.6) + (avg_brightness * 0.4)
        self.model_affinities[model_type] = new_affinity
        
        # Determine trend
        if len(recent_performance) >= 5:
            early_half = recent_performance[:len(recent_performance)//2]
            later_half = recent_performance[len(recent_performance)//2:]
            
            if np.mean(later_half) > np.mean(early_half) + 0.1:
                history['trend'] = 'improving'
            elif np.mean(later_half) < np.mean(early_half) - 0.1:
                history['trend'] = 'declining'
            else:
                history['trend'] = 'stable'

class NetworkModelVotingSystem:
    def __init__(self, tensor_network):
        self.tensor_network = tensor_network
        self.global_model_scores = {}
        
    def calculate_global_model_rankings(self):
        """Aggregate neuron votes to rank models network-wide"""
        
        model_vote_totals = {}
        total_vote_weight = 0
        
        for neuron in self.tensor_network.neurons:
            neuron_weight = neuron.get('vote_weight', 1.0)
            neuron_affinities = neuron.get('model_affinities', {})
            
            for model_type, affinity in neuron_affinities.items():
                if model_type not in model_vote_totals:
                    model_vote_totals[model_type] = 0
                
                # Weighted vote: neuron importance * model affinity
                weighted_vote = neuron_weight * affinity
                model_vote_totals[model_type] += weighted_vote
            
            total_vote_weight += neuron_weight
        
        # Calculate global model scores (0-1 scale)
        global_model_scores = {}
        for model_type, total_votes in model_vote_totals.items():
            global_model_scores[model_type] = total_votes / total_vote_weight
        
        # Sort by performance
        ranked_models = sorted(
            global_model_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return ranked_models, global_model_scores
    
    def allocate_compute_by_neuron_votes(self, total_compute_budget):
        """Allocate compute resources based on neuron voting results"""
        
        ranked_models, global_scores = self.calculate_global_model_rankings()
        
        compute_allocations = {}
        for model_type, score in global_scores.items():
            # Base allocation proportional to votes
            base_allocation = (score / sum(global_scores.values())) * total_compute_budget
            
            # Bonus for models with high neuron diversity (working well across many neuron types)
            diversity_bonus = self.calculate_neuron_diversity_bonus(model_type)
            
            final_allocation = base_allocation * (1 + diversity_bonus)
            compute_allocations[model_type] = final_allocation
        
        return compute_allocations
    
    def calculate_neuron_diversity_bonus(self, model_type):
        """Bonus for models that work well across diverse neuron types"""
        
        successful_neurons = 0
        total_neurons = len(self.tensor_network.neurons)
        
        for neuron in self.tensor_network.neurons:
            model_affinity = neuron.get('model_affinities', {}).get(model_type, 0)
            if model_affinity > 0.6:  # "Success" threshold
                successful_neurons += 1
        
        diversity_ratio = successful_neurons / total_neurons
        
        # Up to 50% bonus for models that work well across 80%+ of neurons
        if diversity_ratio > 0.8:
            return 0.5
        elif diversity_ratio > 0.6:
            return 0.3
        elif diversity_ratio > 0.4:
            return 0.15
        else:
            return 0.0
```

### Distributed Voting Mechanism

```python
def neuron_model_voting_cycle(tensor_network):
    """Execute one cycle of distributed model voting and resource reallocation"""
    
    # 1. Each neuron evaluates recent model performance
    for neuron in tensor_network.neurons:
        selector = NeuronModelSelector(neuron)
        
        # Update opinions based on recent interactions
        recent_interactions = get_recent_model_interactions(neuron['neuron_id'])
        for interaction in recent_interactions:
            selector.update_model_performance(
                interaction['model_type'],
                interaction['success'], 
                interaction['brightness_achieved']
            )
    
    # 2. Aggregate votes to determine global model rankings
    voting_system = NetworkModelVotingSystem(tensor_network)
    model_rankings, global_scores = voting_system.calculate_global_model_rankings()
    
    # 3. Reallocate compute resources based on voting results
    compute_allocations = voting_system.allocate_compute_by_neuron_votes(
        total_compute_budget=100.0
    )
    
    # 4. Spawn/terminate model instances based on neuron preferences
    ecosystem_manager = MultiModelFireflyEcosystem(tensor_network)
    
    for model_type, allocation in compute_allocations.items():
        current_instances = len(ecosystem_manager.active_models.get(model_type, []))
        optimal_instances = int(allocation / 5)  # 5 compute units per instance
        
        if optimal_instances > current_instances:
            # Spawn new instances for popular models
            new_instances = optimal_instances - current_instances
            ecosystem_manager.spawn_additional_instances(model_type, new_instances)
            
        elif optimal_instances < current_instances:
            # Reduce instances for unpopular models
            instances_to_remove = current_instances - optimal_instances
            ecosystem_manager.terminate_underperforming_instances(model_type, instances_to_remove)
    
    return {
        'model_rankings': model_rankings,
        'compute_allocations': compute_allocations,
        'voting_summary': generate_voting_summary(tensor_network)
    }

def generate_voting_summary(tensor_network):
    """Generate human-readable summary of neuron voting results"""
    
    model_vote_counts = {}
    for neuron in tensor_network.neurons:
        affinities = neuron.get('model_affinities', {})
        
        for model_type, affinity in affinities.items():
            if model_type not in model_vote_counts:
                model_vote_counts[model_type] = {'high': 0, 'medium': 0, 'low': 0}
            
            if affinity > 0.7:
                model_vote_counts[model_type]['high'] += 1
            elif affinity > 0.4:
                model_vote_counts[model_type]['medium'] += 1
            else:
                model_vote_counts[model_type]['low'] += 1
    
    summary = "Neuron Voting Results:\n"
    for model_type, counts in model_vote_counts.items():
        total_votes = sum(counts.values())
        high_pct = (counts['high'] / total_votes) * 100
        summary += f"  {model_type}: {high_pct:.1f}% neurons strongly prefer this model\n"
    
    return summary
```

### Bash Integration for Neuron Model Selection

```bash
# Neuron updates model preferences after firefly bot interaction
update_neuron_model_preference() {
    local neuron_key="$1"
    local model_type="$2"
    local success="$3"
    local brightness="$4"
    
    # Create model performance update
    echo "model_update:${model_type}" > ${neuron_key}.model_feedback
    echo "success:${success}" >> ${neuron_key}.model_feedback
    echo "brightness:${brightness}" >> ${neuron_key}.model_feedback
    echo "timestamp:$(date)" >> ${neuron_key}.model_feedback
    
    # Process update in neuron's next iteration
    if [ -f "${neuron_key}.model_feedback" ]; then
        model=$(grep "model_update:" ${neuron_key}.model_feedback | cut -d: -f2)
        success=$(grep "success:" ${neuron_key}.model_feedback | cut -d: -f2)
        brightness=$(grep "brightness:" ${neuron_key}.model_feedback | cut -d: -f2)
        
        # Update JSON neuron's model affinity
        python3 -c "
import json
with open('${neuron_key}.json', 'r') as f:
    neuron = json.load(f)
    
# Update model performance
if 'model_affinities' not in neuron:
    neuron['model_affinities'] = {}
    
current_affinity = neuron['model_affinities'].get('${model}', 0.5)

# Simple learning: successful interactions increase affinity
if '${success}' == 'true':
    new_affinity = min(1.0, current_affinity + 0.1)
else:
    new_affinity = max(0.1, current_affinity - 0.05)
    
neuron['model_affinities']['${model}'] = new_affinity

with open('${neuron_key}.json', 'w') as f:
    json.dump(neuron, f, indent=2)
        "
        
        rm ${neuron_key}.model_feedback
    fi
}

# Network-wide model voting and reallocation
network_voting_cycle() {
    echo "Starting network-wide model voting cycle..."
    
    # Collect votes from all neurons
    total_votes=$(ls *.json | wc -l)
    echo "Collecting votes from $total_votes neurons..."
    
    # Calculate global model rankings
    python3 -c "
import json
import glob
from collections import defaultdict

model_scores = defaultdict(list)

for json_file in glob.glob('*.json'):
    with open(json_file, 'r') as f:
        neuron = json.load(f)
        affinities = neuron.get('model_affinities', {})
        vote_weight = neuron.get('vote_weight', 1.0)
        
        for model, affinity in affinities.items():
            model_scores[model].append(affinity * vote_weight)

# Calculate averages and rank models
print('=== NETWORK VOTING RESULTS ===')
for model in sorted(model_scores.keys()):
    avg_score = sum(model_scores[model]) / len(model_scores[model])
    print(f'{model}: {avg_score:.3f} (from {len(model_scores[model])} neurons)')
    "
}
```