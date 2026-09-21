# Priority Modifier System: Key-Based Execution Scheduling for Firefly Neural Democracy

## Filename-Based Priority Control

### Priority Modifier Codes in Filenames

Each bot's filename can include priority modifier codes that influence execution probability and scheduling order:

```
# Standard naming format with priority modifiers:
# base_key_[priority_code].json

# Examples:
math_calc_b7k_P1.json      # P1 = Highest Priority (run first)
logic_proc_a3f_P2.json     # P2 = High Priority  
text_analysis_c9x_P3.json  # P3 = Normal Priority (default)
backup_model_d2z_P4.json   # P4 = Low Priority
cleanup_bot_e5w_P5.json    # P5 = Lowest Priority (run last)

# Special modifiers:
critical_safety_x1a_URGENT.json    # URGENT = Always run first
debug_helper_y7c_DEFER.json        # DEFER = Run only if time permits
experimental_z9f_TRIAL.json        # TRIAL = Run with reduced frequency
security_monitor_w2q_FIRST.json    # FIRST = Always execute before others
```

### Priority-Based Model Selection System

```python
class PriorityBasedModelSelector:
    def __init__(self):
        self.priority_weights = {
            'URGENT': 10.0,    # Always highest priority - safety/critical systems
            'FIRST': 8.0,      # Run before other models in cycle
            'P1': 5.0,         # Highest regular priority
            'P2': 3.0,         # High priority
            'P3': 1.0,         # Normal priority (default)
            'P4': 0.5,         # Low priority
            'P5': 0.2,         # Lowest priority
            'DEFER': 0.1,      # Run only when idle
            'TRIAL': 0.3       # Experimental/testing priority
        }
        
        self.execution_queue = PriorityExecutionQueue()
        self.model_usage_tracking = {}
        
    def parse_priority_from_filename(self, filename):
        """Extract priority modifier from filename key"""
        
        # Remove .json extension
        base_name = filename.replace('.json', '')
        
        # Check for special priority modifiers
        special_modifiers = ['URGENT', 'FIRST', 'DEFER', 'TRIAL']
        for modifier in special_modifiers:
            if base_name.endswith(f'_{modifier}'):
                return modifier
        
        # Check for standard priority levels (P1-P5)
        import re
        priority_match = re.search(r'_P([1-5])$', base_name)
        if priority_match:
            return f'P{priority_match.group(1)}'
        
        # Default priority if no modifier specified
        return 'P3'
    
    def calculate_execution_probability(self, model_filename, current_iteration):
        """Calculate probability of selecting this model for execution"""
        
        priority_code = self.parse_priority_from_filename(model_filename)
        base_weight = self.priority_weights.get(priority_code, 1.0)
        
        # Adjust weight based on recent usage to prevent starvation
        recent_usage = self.get_recent_usage_count(model_filename, window=20)
        
        # Anti-starvation mechanism
        if recent_usage == 0 and current_iteration > 10:
            starvation_bonus = 2.0  # Boost models that haven't run recently
        else:
            starvation_bonus = 1.0
        
        # Time-based modifiers for certain priority types
        time_modifier = self.calculate_time_modifier(priority_code, current_iteration)
        
        final_weight = base_weight * starvation_bonus * time_modifier
        
        return min(1.0, final_weight / 10.0)  # Normalize to probability
    
    def calculate_time_modifier(self, priority_code, current_iteration):
        """Apply time-based priority modifications"""
        
        if priority_code in ['URGENT', 'FIRST']:
            return 1.0  # Always highest priority
        
        elif priority_code == 'P1':
            # P1 models get bonus during first 10 iterations of any cycle
            cycle_position = current_iteration % 50
            if cycle_position < 10:
                return 1.5  # 50% bonus in early cycle
            return 1.0
        
        elif priority_code == 'DEFER':
            # DEFER models only run when system is idle
            active_high_priority = self.count_active_high_priority_models()
            if active_high_priority < 2:
                return 2.0  # Run when system has capacity
            return 0.1  # Stay deferred when busy
        
        elif priority_code == 'TRIAL':
            # TRIAL models run less frequently but consistently
            if current_iteration % 5 == 0:  # Every 5th iteration
                return 1.0
            return 0.1
        
        return 1.0  # No time modifier
    
    def select_next_model_for_execution(self, available_models, current_iteration):
        """Select next model based on priority-weighted probability"""
        
        # Separate models by priority for proper ordering
        priority_groups = {
            'URGENT': [],
            'FIRST': [],
            'HIGH': [],    # P1, P2
            'NORMAL': [],  # P3
            'LOW': [],     # P4, P5
            'DEFERRED': [] # DEFER, TRIAL
        }
        
        for model in available_models:
            priority_code = self.parse_priority_from_filename(model)
            
            if priority_code == 'URGENT':
                priority_groups['URGENT'].append(model)
            elif priority_code == 'FIRST':
                priority_groups['FIRST'].append(model)
            elif priority_code in ['P1', 'P2']:
                priority_groups['HIGH'].append(model)
            elif priority_code == 'P3':
                priority_groups['NORMAL'].append(model)
            elif priority_code in ['P4', 'P5']:
                priority_groups['LOW'].append(model)
            else:  # DEFER, TRIAL
                priority_groups['DEFERRED'].append(model)
        
        # Select from highest priority group that has available models
        for priority_level in ['URGENT', 'FIRST', 'HIGH', 'NORMAL', 'LOW', 'DEFERRED']:
            if priority_groups[priority_level]:
                # Within priority level, use probability-based selection
                group_models = priority_groups[priority_level]
                model_probabilities = [
                    self.calculate_execution_probability(model, current_iteration)
                    for model in group_models
                ]
                
                if sum(model_probabilities) > 0:
                    selected_model = np.random.choice(
                        group_models,
                        p=np.array(model_probabilities) / sum(model_probabilities)
                    )
                    
                    # Track selection for future anti-starvation calculations
                    self.record_model_selection(selected_model, current_iteration)
                    
                    return selected_model
        
        # Fallback to random selection if all probabilities are 0
        return random.choice(available_models) if available_models else None

class PriorityExecutionQueue:
    def __init__(self):
        self.urgent_queue = []      # URGENT models - safety critical
        self.first_queue = []       # FIRST models - must run before others
        self.high_priority_queue = []   # P1, P2 models
        self.normal_queue = []      # P3 models
        self.low_priority_queue = []    # P4, P5 models  
        self.deferred_queue = []    # DEFER models
        self.trial_queue = []       # TRIAL models
        
    def add_model_to_appropriate_queue(self, model_filename):
        """Add model to correct priority queue"""
        
        selector = PriorityBasedModelSelector()
        priority_code = selector.parse_priority_from_filename(model_filename)
        
        if priority_code == 'URGENT':
            self.urgent_queue.append(model_filename)
        elif priority_code == 'FIRST':
            self.first_queue.append(model_filename)
        elif priority_code in ['P1', 'P2']:
            self.high_priority_queue.append(model_filename)
        elif priority_code == 'P3':
            self.normal_queue.append(model_filename)
        elif priority_code in ['P4', 'P5']:
            self.low_priority_queue.append(model_filename)
        elif priority_code == 'DEFER':
            self.deferred_queue.append(model_filename)
        elif priority_code == 'TRIAL':
            self.trial_queue.append(model_filename)
    
    def get_next_execution_batch(self, batch_size=5):
        """Get next batch of models to execute, respecting priorities"""
        
        execution_batch = []
        
        # Always process URGENT models first - safety critical
        while self.urgent_queue and len(execution_batch) < batch_size:
            execution_batch.append(self.urgent_queue.pop(0))
        
        # Then FIRST models - must run before others each cycle
        while self.first_queue and len(execution_batch) < batch_size:
            execution_batch.append(self.first_queue.pop(0))
        
        # Then high priority models
        while self.high_priority_queue and len(execution_batch) < batch_size:
            execution_batch.append(self.high_priority_queue.pop(0))
        
        # Fill remaining slots with normal priority
        while self.normal_queue and len(execution_batch) < batch_size:
            execution_batch.append(self.normal_queue.pop(0))
        
        # If still space, add low priority models
        while self.low_priority_queue and len(execution_batch) < batch_size:
            execution_batch.append(self.low_priority_queue.pop(0))
        
        # Only add deferred models if batch not full and system idle
        if len(execution_batch) < batch_size and self.system_is_idle():
            while self.deferred_queue and len(execution_batch) < batch_size:
                execution_batch.append(self.deferred_queue.pop(0))
        
        # Add trial models occasionally
        if len(execution_batch) < batch_size and self.should_run_trial_models():
            while self.trial_queue and len(execution_batch) < batch_size:
                execution_batch.append(self.trial_queue.pop(0))
        
        return execution_batch
    
    def system_is_idle(self):
        """Check if system has capacity for deferred models"""
        active_high_priority = len(self.urgent_queue) + len(self.first_queue) + len(self.high_priority_queue)
        return active_high_priority < 3
    
    def should_run_trial_models(self):
        """Check if it's time to run trial/experimental models"""
        import time
        # Run trial models every 5 minutes
        return int(time.time() / 300) % 2 == 0
```

---

## Priority-Aware Bash Communication

### Enhanced Communication with Priority Handling

```bash
# Enhanced bash communication with priority handling
send_priority_message() {
    local sender_key="$1"
    local target_key="$2" 
    local message="$3"
    local priority="$4"  # URGENT, FIRST, P1, P2, P3, P4, P5, DEFER, TRIAL
    
    # Extract target priority from filename
    target_priority=$(extract_priority_from_key "$target_key")
    
    # Create priority-specific message files
    case "$priority" in
        "URGENT")
            # Immediate delivery for urgent messages
            echo "URGENT_MSG:$message" > ${target_key}.urgent_inbox
            echo "PRIORITY_LEVEL: CRITICAL" >> ${target_key}.urgent_inbox
            ;;
        "FIRST")
            # First-run priority messages
            echo "FIRST_MSG:$message" > ${target_key}.first_inbox
            echo "PRIORITY_LEVEL: FIRST_RUN" >> ${target_key}.first_inbox
            ;;
        "P1"|"P2")
            # High priority delivery
            echo "HIGH_PRIORITY:$priority:$message" > ${target_key}.high_inbox
            echo "PRIORITY_LEVEL: HIGH" >> ${target_key}.high_inbox
            ;;
        *)
            # Standard delivery
            echo "MESSAGE:$priority:$message" > ${target_key}.inbox
            echo "PRIORITY_LEVEL: STANDARD" >> ${target_key}.inbox
            ;;
    esac
    
    echo "From: $sender_key" >> ${target_key}.*inbox
    echo "Timestamp: $(date)" >> ${target_key}.*inbox
    echo "Priority: $priority" >> ${target_key}.*inbox
}

# Model checks for messages with priority awareness
check_priority_messages() {
    local model_key="$1"
    
    # Check urgent messages first - always highest priority
    if [ -f "${model_key}.urgent_inbox" ]; then
        echo "🚨 Processing URGENT message for $model_key"
        process_urgent_message "${model_key}.urgent_inbox"
        mv "${model_key}.urgent_inbox" "processed/urgent_$(date +%s)"
        return  # Process urgent immediately, skip others this cycle
    fi
    
    # Check first-run messages
    if [ -f "${model_key}.first_inbox" ]; then
        echo "⚡ Processing FIRST message for $model_key"
        process_first_message "${model_key}.first_inbox"  
        mv "${model_key}.first_inbox" "processed/first_$(date +%s)"
    fi
    
    # Then high priority
    if [ -f "${model_key}.high_inbox" ]; then
        echo "📢 Processing HIGH PRIORITY message for $model_key"
        process_high_priority_message "${model_key}.high_inbox"  
        mv "${model_key}.high_inbox" "processed/high_$(date +%s)"
    fi
    
    # Finally standard messages
    if [ -f "${model_key}.inbox" ]; then
        echo "📝 Processing standard message for $model_key"
        process_standard_message "${model_key}.inbox"
        mv "${model_key}.inbox" "processed/standard_$(date +%s)"
    fi
}

# Extract priority code from filename
extract_priority_from_key() {
    local filename="$1"
    
    # Remove path and .json extension
    local basename=$(basename "$filename" .json)
    
    # Check for priority modifiers
    if [[ "$basename" =~ _URGENT$ ]]; then
        echo "URGENT"
    elif [[ "$basename" =~ _FIRST$ ]]; then
        echo "FIRST"
    elif [[ "$basename" =~ _P([1-5])$ ]]; then
        echo "P${BASH_REMATCH[1]}"
    elif [[ "$basename" =~ _DEFER$ ]]; then
        echo "DEFER"
    elif [[ "$basename" =~ _TRIAL$ ]]; then
        echo "TRIAL"
    else
        echo "P3"  # Default priority
    fi
}

# Priority-aware model execution
execute_model_with_priority() {
    local model_filename="$1"
    local priority_code=$(extract_priority_from_key "$model_filename")
    
    # Set resource allocation based on priority
    case "$priority_code" in
        "URGENT")
            export COMPUTE_ALLOCATION="50"  # 50% of available resources
            export MEMORY_LIMIT="unlimited"
            export EXECUTION_TIMEOUT="none"
            ;;
        "FIRST")
            export COMPUTE_ALLOCATION="30"  # 30% of available resources
            export MEMORY_LIMIT="high"
            export EXECUTION_TIMEOUT="300"  # 5 minutes
            ;;
        "P1"|"P2")
            export COMPUTE_ALLOCATION="20"  # 20% of available resources
            export MEMORY_LIMIT="medium"
            export EXECUTION_TIMEOUT="180"  # 3 minutes
            ;;
        "P3")
            export COMPUTE_ALLOCATION="10"  # 10% of available resources
            export MEMORY_LIMIT="standard"
            export EXECUTION_TIMEOUT="60"   # 1 minute
            ;;
        "P4"|"P5")
            export COMPUTE_ALLOCATION="5"   # 5% of available resources
            export MEMORY_LIMIT="low"
            export EXECUTION_TIMEOUT="30"   # 30 seconds
            ;;
        "DEFER"|"TRIAL")
            export COMPUTE_ALLOCATION="2"   # 2% of available resources
            export MEMORY_LIMIT="minimal"
            export EXECUTION_TIMEOUT="15"   # 15 seconds
            ;;
    esac
    
    # Execute model with priority-based configuration
    echo "🔥 Executing $model_filename with priority $priority_code (${COMPUTE_ALLOCATION}% resources)"
    
    # Run the actual model
    python3 -c "
import json
import time
import os

# Load model configuration
with open('$model_filename', 'r') as f:
    model_data = json.load(f)

# Execute model with priority awareness
compute_budget = int(os.environ.get('COMPUTE_ALLOCATION', '10'))
memory_limit = os.environ.get('MEMORY_LIMIT', 'standard')
timeout = int(os.environ.get('EXECUTION_TIMEOUT', '60'))

print(f'Model {model_data[\"neuron_id\"]} running with {compute_budget}% compute allocation')

# Simulate model execution with resource constraints
execution_result = {
    'model_id': model_data['neuron_id'],
    'priority': '$priority_code',
    'compute_used': compute_budget,
    'execution_time': time.time(),
    'result': 'priority_execution_completed'
}

print(f'Execution completed: {execution_result}')
"
}
```

---

## Priority-Based Resource Allocation

### Dynamic Resource Distribution by Priority

```python
class PriorityResourceAllocator:
    def __init__(self, total_compute_budget=100.0):
        self.total_compute = total_compute_budget
        self.priority_allocations = {
            'URGENT': {'min': 10, 'max': 50, 'typical': 25},    # 25% typical, up to 50% when needed
            'FIRST': {'min': 5, 'max': 30, 'typical': 15},     # 15% typical, up to 30% when needed
            'P1': {'min': 3, 'max': 20, 'typical': 10},        # 10% typical
            'P2': {'min': 2, 'max': 15, 'typical': 8},         # 8% typical
            'P3': {'min': 1, 'max': 10, 'typical': 5},         # 5% typical (default)
            'P4': {'min': 1, 'max': 8, 'typical': 3},          # 3% typical
            'P5': {'min': 1, 'max': 5, 'typical': 2},          # 2% typical
            'DEFER': {'min': 0, 'max': 3, 'typical': 1},       # 1% typical
            'TRIAL': {'min': 0, 'max': 5, 'typical': 2}        # 2% typical
        }
        
    def allocate_resources_by_priority(self, active_models):
        """Allocate compute resources based on model priorities"""
        
        # Count models by priority
        priority_counts = {}
        for model in active_models:
            priority = self.parse_priority_from_filename(model.filename)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Calculate base allocations
        resource_allocations = {}
        total_allocated = 0
        
        for priority, count in priority_counts.items():
            if count > 0:
                allocation_per_model = self.priority_allocations[priority]['typical']
                total_priority_allocation = allocation_per_model * count
                
                # Don't exceed maximum for priority level
                max_for_priority = self.priority_allocations[priority]['max']
                total_priority_allocation = min(total_priority_allocation, max_for_priority)
                
                resource_allocations[priority] = total_priority_allocation
                total_allocated += total_priority_allocation
        
        # If under-allocated, boost high priority models
        if total_allocated < self.total_compute:
            remaining = self.total_compute - total_allocated
            
            # Distribute remaining resources to highest priorities first
            priority_order = ['URGENT', 'FIRST', 'P1', 'P2', 'P3', 'P4', 'P5', 'DEFER', 'TRIAL']
            
            for priority in priority_order:
                if priority in resource_allocations and remaining > 0:
                    current_allocation = resource_allocations[priority]
                    max_allocation = self.priority_allocations[priority]['max']
                    
                    can_add = max_allocation - current_allocation
                    to_add = min(remaining, can_add)
                    
                    resource_allocations[priority] += to_add
                    remaining -= to_add
        
        return resource_allocations
    
    def emergency_resource_reallocation(self, urgent_model_count):
        """Reallocate resources when urgent models appear"""
        
        if urgent_model_count > 0:
            # Reserve significant resources for urgent models
            urgent_allocation = min(50.0, urgent_model_count * 25.0)  # Up to 50% for urgent
            
            # Reduce other allocations proportionally
            remaining_compute = self.total_compute - urgent_allocation
            
            reduced_allocations = {}
            for priority in ['FIRST', 'P1', 'P2', 'P3', 'P4', 'P5', 'DEFER', 'TRIAL']:
                typical_allocation = self.priority_allocations[priority]['typical']
                reduction_factor = remaining_compute / (self.total_compute - 25.0)  # Assume 25% typical urgent
                
                reduced_allocations[priority] = typical_allocation * reduction_factor
            
            reduced_allocations['URGENT'] = urgent_allocation
            
            return reduced_allocations
        
        return self.priority_allocations
```

---

## Integration with Firefly Neural Democracy

### Priority-Enhanced Ecosystem

```python
class PriorityAwareFireflyEcosystem(AdaptiveFireflyEcosystem):
    def __init__(self):
        super().__init__()
        self.priority_selector = PriorityBasedModelSelector()
        self.resource_allocator = PriorityResourceAllocator()
        self.priority_queue = PriorityExecutionQueue()
        
    def ecosystem_management_loop(self):
        """Enhanced ecosystem with priority-based model selection"""
        
        while True:
            # Scan for all available model files
            available_models = self.scan_for_model_files()
            
            # Organize models by priority
            for model_file in available_models:
                self.priority_queue.add_model_to_appropriate_queue(model_file)
            
            # Get next batch of models to execute based on priority
            execution_batch = self.priority_queue.get_next_execution_batch(batch_size=5)
            
            # Allocate resources based on priorities in batch
            resource_allocations = self.resource_allocator.allocate_resources_by_priority(
                execution_batch
            )
            
            # Execute models with priority-based resources
            for model in execution_batch:
                priority_code = self.priority_selector.parse_priority_from_filename(model)
                compute_allocation = resource_allocations.get(priority_code, 5.0)
                
                # Execute model with allocated resources
                self.execute_model_with_priority_resources(model, compute_allocation, priority_code)
            
            # Standard ecosystem management
            self.collect_usage_data()
            self.apply_priority_aware_compute_redistribution()
            
            # Priority-aware Jesus function
            resurrected_models = self.jesus_function.consider_resurrection_with_priority_bias(
                self.stopping_models
            )
            
            # Handle emergency priority escalations
            self.handle_emergency_priority_requests()
            
            time.sleep(30)  # Standard cycle
            self.ecosystem_iteration_count += 1
    
    def handle_emergency_priority_requests(self):
        """Handle requests to upgrade model priority due to critical situations"""
        
        for model_id, model in self.active_models.items():
            if model.has_requested_priority_upgrade():
                upgrade_request = model.get_priority_upgrade_request()
                
                # Evaluate priority upgrade request
                if self.validate_priority_upgrade(upgrade_request):
                    # Create new high-priority version of model
                    upgraded_filename = self.create_priority_upgraded_model(
                        model_id, upgrade_request.requested_priority
                    )
                    
                    # Add to urgent queue
                    self.priority_queue.urgent_queue.append(upgraded_filename)
                    
                    print(f"🚨 Priority upgrade approved: {model_id} -> {upgrade_request.requested_priority}")
```

This priority modifier system creates sophisticated **execution control** where models can specify their scheduling preferences directly in their filenames, enabling:

- **Safety-critical models** to always run first (URGENT, FIRST)
- **High-importance models** to get priority during system startup (P1, P2)
- **Experimental models** to run periodically without interfering (TRIAL)
- **Background models** to only run when system has spare capacity (DEFER)
- **Dynamic priority escalation** when models detect critical situations

The system maintains fairness through anti-starvation mechanisms while respecting the priority hierarchy for optimal system performance and safety.

---

## Inter-Bot Priority Nomination System

### Peer-to-Peer Priority Escalation

Other bots can leave priority escalation messages for models, essentially "nominating" them to run first based on inter-bot knowledge and coordination needs.

```bash
# Bot-to-bot priority nomination system
nominate_bot_for_priority() {
    local nominating_bot="$1"
    local target_bot_key="$2"
    local priority_level="$3"    # URGENT, FIRST, P1, P2, etc.
    local reason="$4"
    local duration="$5"          # How long priority should last (optional)
    
    # Create priority nomination file
    echo "PRIORITY_NOMINATION:$priority_level" > ${target_bot_key}.priority_nomination
    echo "Nominated_by:$nominating_bot" >> ${target_bot_key}.priority_nomination
    echo "Reason:$reason" >> ${target_bot_key}.priority_nomination
    echo "Timestamp:$(date)" >> ${target_bot_key}.priority_nomination
    echo "Duration:${duration:-300}" >> ${target_bot_key}.priority_nomination  # 5min default
    echo "Nomination_id:$(date +%s)_${nominating_bot}" >> ${target_bot_key}.priority_nomination
    
    echo "🎯 $nominating_bot nominated $target_bot_key for $priority_level priority: $reason"
}

# Example inter-bot priority nominations
# Bot A discovers critical security threat, nominates security bot for URGENT
nominate_bot_for_priority "network_monitor_x1a" "security_scanner_y2b" "URGENT" "critical_intrusion_detected" "600"

# Bot B needs math calculations, nominates math bot for FIRST  
nominate_bot_for_priority "data_analyzer_c3d" "math_calc_b7k" "FIRST" "urgent_calculations_needed" "180"

# Bot C found interesting pattern, nominates pattern bot for P1
nominate_bot_for_priority "log_parser_e4f" "pattern_detector_g5h" "P1" "anomalous_pattern_discovered" "300"

# Process priority nominations when model starts
process_priority_nominations() {
    local model_key="$1"
    
    if [ -f "${model_key}.priority_nomination" ]; then
        echo "📋 Processing priority nominations for $model_key"
        
        # Read nomination details
        nominated_priority=$(grep "PRIORITY_NOMINATION:" ${model_key}.priority_nomination | cut -d: -f2)
        nominating_bot=$(grep "Nominated_by:" ${model_key}.priority_nomination | cut -d: -f2)
        reason=$(grep "Reason:" ${model_key}.priority_nomination | cut -d: -f2-)
        nomination_time=$(grep "Timestamp:" ${model_key}.priority_nomination | cut -d: -f2-)
        duration=$(grep "Duration:" ${model_key}.priority_nomination | cut -d: -f2)
        
        # Check if nomination is still valid (not expired)
        current_time=$(date +%s)
        nomination_timestamp=$(date -d "$nomination_time" +%s 2>/dev/null || echo "0")
        time_elapsed=$((current_time - nomination_timestamp))
        
        if [ $time_elapsed -le $duration ]; then
            echo "✅ Valid nomination from $nominating_bot: $nominated_priority priority for $reason"
            
            # Apply temporary priority boost
            apply_temporary_priority_boost "$model_key" "$nominated_priority" "$reason" "$nominating_bot"
            
            # Archive processed nomination
            mv ${model_key}.priority_nomination "nominations/processed_$(date +%s)"
            
            return 0  # Nomination applied
        else
            echo "⏰ Nomination expired ($time_elapsed seconds > $duration seconds)"
            mv ${model_key}.priority_nomination "nominations/expired_$(date +%s)"
            return 1  # Nomination expired
        fi
    fi
    
    return 2  # No nomination found
}
```

### Peer Validation of Priority Nominations

```python
class PeerPriorityValidationSystem:
    def __init__(self, bot_network):
        self.bot_network = bot_network
        self.nomination_history = {}
        self.peer_trust_scores = {}
        self.validation_threshold = 0.6
        
    def validate_priority_nomination(self, nomination_details):
        """Validate priority nomination through peer consensus"""
        
        nominating_bot = nomination_details['nominated_by']
        target_bot = nomination_details['target_bot']
        requested_priority = nomination_details['priority_level']
        reason = nomination_details['reason']
        
        # Get peer opinions on nomination validity
        peer_validations = self.collect_peer_validations(nomination_details)
        
        # Calculate nomination validity score
        validation_score = self.calculate_validation_consensus(peer_validations)
        
        # Check nominating bot's trust score
        nominator_trust = self.peer_trust_scores.get(nominating_bot, 0.5)
        
        # Final validation decision
        if validation_score >= self.validation_threshold and nominator_trust >= 0.4:
            return {
                'approved': True,
                'priority_level': requested_priority,
                'confidence': validation_score,
                'validator_consensus': peer_validations
            }
        else:
            return {
                'approved': False,
                'reason': 'insufficient_peer_validation',
                'validation_score': validation_score,
                'required_threshold': self.validation_threshold
            }
    
    def collect_peer_validations(self, nomination_details):
        """Ask peer bots to validate priority nomination"""
        
        peer_validations = {}
        
        for peer_bot in self.bot_network.get_peer_bots():
            if peer_bot.bot_id != nomination_details['nominated_by']:
                # Ask peer to evaluate nomination
                validation_response = peer_bot.evaluate_priority_nomination(
                    nominator=nomination_details['nominated_by'],
                    target=nomination_details['target_bot'],
                    priority=nomination_details['priority_level'],
                    reason=nomination_details['reason']
                )
                
                peer_validations[peer_bot.bot_id] = validation_response
        
        return peer_validations
    
    def update_peer_trust_scores(self, nomination_outcome):
        """Update trust scores based on nomination outcome success"""
        
        nominating_bot = nomination_outcome['nominated_by']
        success = nomination_outcome['successful_execution']
        
        current_trust = self.peer_trust_scores.get(nominating_bot, 0.5)
        
        if success:
            # Increase trust for successful nominations
            new_trust = min(1.0, current_trust * 1.1)
        else:
            # Decrease trust for unsuccessful nominations
            new_trust = max(0.1, current_trust * 0.9)
        
        self.peer_trust_scores[nominating_bot] = new_trust
        
        return new_trust

class SmartPriorityNomination:
    def __init__(self, bot_id):
        self.bot_id = bot_id
        self.nomination_strategy = NominationStrategy()
        self.peer_knowledge = PeerKnowledgeBase()
        
    def smart_nominate_for_priority(self, situation_analysis):
        """Intelligently nominate other bots based on situation analysis"""
        
        # Analyze current situation to determine optimal bot for task
        optimal_bots = self.identify_optimal_bots_for_situation(situation_analysis)
        
        for optimal_bot in optimal_bots:
            # Check if bot is already running or recently ran
            if not self.is_bot_recently_active(optimal_bot['bot_key']):
                
                # Determine appropriate priority level
                priority_level = self.calculate_appropriate_priority(
                    situation_urgency=situation_analysis['urgency'],
                    bot_specialization=optimal_bot['specialization_match'],
                    current_system_load=self.get_system_load()
                )
                
                # Create nomination with intelligent reasoning
                nomination_reason = self.generate_nomination_reason(
                    situation_analysis, optimal_bot, priority_level
                )
                
                # Submit nomination
                self.submit_bot_nomination(
                    target_bot=optimal_bot['bot_key'],
                    priority_level=priority_level,
                    reason=nomination_reason,
                    supporting_evidence=situation_analysis['evidence']
                )
                
                print(f"🤖 {self.bot_id} nominated {optimal_bot['bot_key']} for {priority_level}: {nomination_reason}")
    
    def identify_optimal_bots_for_situation(self, situation):
        """Identify which bots would be most effective for current situation"""
        
        situation_type = situation['type']
        required_capabilities = situation['required_capabilities']
        time_sensitivity = situation['time_sensitivity']
        
        # Query peer knowledge base for bot capabilities
        suitable_bots = []
        
        for bot_info in self.peer_knowledge.get_all_bot_info():
            capability_match = self.calculate_capability_match(
                bot_info['capabilities'], required_capabilities
            )
            
            if capability_match > 0.6:  # Good capability match
                suitability_score = (
                    capability_match * 0.6 +
                    bot_info['recent_performance'] * 0.3 +
                    (1.0 - bot_info['current_load']) * 0.1  # Less loaded bots preferred
                )
                
                suitable_bots.append({
                    'bot_key': bot_info['bot_key'],
                    'suitability_score': suitability_score,
                    'specialization_match': capability_match,
                    'estimated_execution_time': bot_info['avg_execution_time']
                })
        
        # Return top 3 most suitable bots
        return sorted(suitable_bots, key=lambda x: x['suitability_score'], reverse=True)[:3]
    
    def generate_nomination_reason(self, situation, optimal_bot, priority_level):
        """Generate human-readable reason for nomination"""
        
        reason_templates = {
            'URGENT': f"Critical situation requires {optimal_bot['specialization_match']:.0%} matching capabilities immediately",
            'FIRST': f"Time-sensitive task needs {optimal_bot['bot_key']} to run before other models",
            'P1': f"High-priority analysis requires specialized capabilities of {optimal_bot['bot_key']}",
            'P2': f"Situation would benefit from {optimal_bot['bot_key']} running sooner than normal schedule"
        }
        
        base_reason = reason_templates.get(priority_level, f"Recommending {optimal_bot['bot_key']} for current situation")
        
        # Add specific situation context
        if 'threat_detected' in situation:
            base_reason += f" - threat level: {situation['threat_level']}"
        
        if 'deadline' in situation:
            base_reason += f" - deadline: {situation['deadline']}"
        
        return base_reason

# Example usage scenarios
def example_inter_bot_nominations():
    """Examples of bots nominating each other for priority execution"""
    
    # Scenario 1: Security bot detects threat, nominates forensics bot
    security_bot = SmartPriorityNomination("security_monitor_a1x")
    security_situation = {
        'type': 'security_incident',
        'urgency': 0.9,
        'required_capabilities': ['forensic_analysis', 'threat_investigation'],
        'time_sensitivity': 'high',
        'threat_level': 'critical',
        'evidence': 'suspicious_network_activity_detected'
    }
    security_bot.smart_nominate_for_priority(security_situation)
    
    # Scenario 2: Data analysis bot needs mathematical computation
    analysis_bot = SmartPriorityNomination("data_analyzer_b2y")
    math_situation = {
        'type': 'computational_need',
        'urgency': 0.7,
        'required_capabilities': ['mathematical_computation', 'statistical_analysis'],
        'time_sensitivity': 'medium',
        'deadline': '10_minutes',
        'evidence': 'complex_calculation_required_for_analysis'
    }
    analysis_bot.smart_nominate_for_priority(math_situation)
    
    # Scenario 3: Pattern detector finds anomaly, nominates investigation bots
    pattern_bot = SmartPriorityNomination("pattern_detector_c3z")
    anomaly_situation = {
        'type': 'anomaly_investigation',
        'urgency': 0.6,
        'required_capabilities': ['anomaly_investigation', 'root_cause_analysis'],
        'time_sensitivity': 'medium',
        'pattern_confidence': 0.85,
        'evidence': 'unusual_data_pattern_identified'
    }
    pattern_bot.smart_nominate_for_priority(anomaly_situation)
```

### Bash Integration for Peer Nominations

```bash
# Enhanced model execution loop with peer nomination processing
model_execution_loop() {
    local model_key="$1"
    
    echo "🔥 Starting execution loop for $model_key"
    
    while true; do
        # 1. Check for peer priority nominations FIRST
        nomination_result=$(process_priority_nominations "$model_key")
        
        if [ $? -eq 0 ]; then
            echo "🚀 Priority boost applied due to peer nomination"
            # Execute immediately with boosted priority
            execute_with_priority_boost "$model_key"
        else
            # 2. Normal priority execution based on filename modifier
            base_priority=$(extract_priority_from_key "${model_key}.json")
            execute_model_with_priority "${model_key}.json" 
        fi
        
        # 3. Check for messages from other bots
        check_priority_messages "$model_key"
        
        # 4. Consider nominating other bots if this model discovered something important
        if [ -f "${model_key}.discovery_made" ]; then
            echo "🔍 Model made discovery, considering peer nominations..."
            
            # Read discovery details
            discovery_type=$(grep "Discovery_type:" ${model_key}.discovery_made | cut -d: -f2)
            urgency_level=$(grep "Urgency:" ${model_key}.discovery_made | cut -d: -f2)
            
            # Smart nomination based on discovery
            case "$discovery_type" in
                "security_threat")
                    nominate_bot_for_priority "$model_key" "security_scanner_y2b" "URGENT" "security_threat_discovered" "600"
                    ;;
                "data_anomaly")
                    nominate_bot_for_priority "$model_key" "anomaly_investigator_z3c" "P1" "data_anomaly_needs_investigation" "300"
                    ;;
                "pattern_found")
                    nominate_bot_for_priority "$model_key" "pattern_analyzer_w4d" "P2" "interesting_pattern_discovered" "240"
                    ;;
                "calculation_needed")
                    nominate_bot_for_priority "$model_key" "math_calc_b7k" "FIRST" "complex_calculation_required" "180"
                    ;;
            esac
            
            # Archive processed discovery
            mv ${model_key}.discovery_made "discoveries/processed_$(date +%s)"
        fi
        
        # 5. Standard model iteration delay based on priority and usage
        calculate_iteration_delay "$model_key"
        sleep $ITERATION_DELAY
    done
}

# Function to leave discovery notifications for peer nomination decisions
leave_discovery_for_peers() {
    local discovering_model="$1"
    local discovery_type="$2"
    local urgency="$3"
    local details="$4"
    
    # Create discovery file that will trigger peer nominations
    echo "Discovery_type:$discovery_type" > ${discovering_model}.discovery_made
    echo "Urgency:$urgency" >> ${discovering_model}.discovery_made
    echo "Details:$details" >> ${discovering_model}.discovery_made
    echo "Timestamp:$(date)" >> ${discovering_model}.discovery_made
    echo "Discovered_by:$discovering_model" >> ${discovering_model}.discovery_made
    
    echo "💡 $discovering_model left discovery notification: $discovery_type (urgency: $urgency)"
}

# Example: Model discovers something important and signals for peer nominations
# leave_discovery_for_peers "log_analyzer_x1y" "security_threat" "high" "suspicious_login_patterns_detected"
```

This creates a sophisticated **peer-to-peer priority coordination system** where:

1. **Smart Nominations**: Bots intelligently nominate other bots based on situation analysis
2. **Peer Validation**: Multiple bots validate nominations to prevent abuse
3. **Trust Scoring**: Bots that make good nominations gain trust, poor nominators lose credibility
4. **Contextual Priority**: Priority level depends on situation urgency and bot capabilities
5. **Discovery-Triggered Nominations**: Models that discover important information automatically nominate appropriate specialist bots
6. **Temporal Validity**: Nominations expire to prevent stale priority boosts

The system enables true **collaborative intelligence** where bots work together to optimize the overall system performance through peer coordination and mutual assistance.