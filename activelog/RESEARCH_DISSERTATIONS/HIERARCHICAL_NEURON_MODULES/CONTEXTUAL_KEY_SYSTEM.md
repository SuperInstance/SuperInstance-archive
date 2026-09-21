# Contextual Key System: Filename-as-Context Architecture
## Self-Documenting Neural Network Through Semantic File Naming

---

## Core Principle: Key = Context = Function

The filename itself contains all the context needed for any firefly bot to understand:
- **What this neuron does**
- **When to use it** 
- **How it fits into the larger system**
- **What kind of input/output to expect**

No documentation reading required - the key IS the documentation.

---

## Contextual Filename Structure

### Standard Contextual Key Format
```
{function_description}_{specialization}_{performance_indicator}_{neuron_id}.json

Examples:
analyze_cryptocurrency_sentiment_from_social_media_expert_87pct_n42k.json
detect_micro_expressions_in_facial_video_specialist_93pct_n81m.json
optimize_product_recommendations_using_purchase_history_master_91pct_n95z.json
```

### Enhanced Context Embedding
```
{action}_{domain}_{method}_{expertise_level}_{success_rate}_{resource_class}_{neuron_id}.json

Examples:
predict_stock_prices_using_sentiment_analysis_expert_89pct_medium_n33x.json
generate_creative_stories_with_character_development_master_94pct_large_n67y.json
translate_languages_preserving_cultural_context_specialist_86pct_small_n29w.json
```

### Contextual Abbreviations for Long Functions
When full description exceeds filesystem limits:
```
crypto_sentiment_analyzer_expert_87pct_n42k.json
facial_micro_expr_detector_spec_93pct_n81m.json  
product_recommender_purchase_based_master_91pct_n95z.json
```

---

## Context Categories in Filenames

### Action Context (What it does)
```
analyze_* - Data analysis neurons
generate_* - Creative/generative neurons  
predict_* - Forecasting neurons
optimize_* - Performance improvement neurons
detect_* - Pattern recognition neurons
classify_* - Categorization neurons
translate_* - Conversion/transformation neurons
monitor_* - Surveillance/tracking neurons
coordinate_* - Management/orchestration neurons
validate_* - Quality assurance neurons
```

### Domain Context (What it works on)
```
*_cryptocurrency_* - Crypto market domain
*_facial_expressions_* - Computer vision domain
*_customer_behavior_* - Business analytics domain
*_protein_structures_* - Bioinformatics domain
*_climate_data_* - Environmental science domain
*_social_media_* - Social network analysis domain
*_natural_language_* - NLP domain
*_financial_markets_* - Finance domain
```

### Method Context (How it works)
```
*_using_machine_learning_* - ML-based approach
*_with_statistical_analysis_* - Statistics-based
*_via_neural_networks_* - Deep learning approach
*_through_pattern_matching_* - Pattern recognition
*_by_sentiment_analysis_* - Sentiment-based method
*_from_historical_data_* - Historical analysis
*_with_real_time_processing_* - Real-time method
```

### Expertise Context (Skill level)
```
*_novice_* - Basic capability, learning mode
*_specialist_* - Focused expertise in narrow area
*_expert_* - High competency, proven performance
*_master_* - Top-tier capability, teaches others
*_coordinator_* - Manages other neurons
*_validator_* - Quality control specialist
```

### Performance Context (Success metrics)
```
*_67pct_* - 67% success rate
*_89pct_* - 89% success rate  
*_95pct_* - 95% success rate
*_realtime_* - Real-time processing capability
*_batch_* - Batch processing optimized
*_lowpower_* - Energy efficient
*_highaccuracy_* - Accuracy optimized
```

---

## Contextual Navigation Examples

### Firefly Bot Contextual Understanding
```python
class ContextualFireflyBot:
    def parse_neuron_context_from_filename(self, filename):
        """Extract complete context from neuron filename"""
        
        # Parse filename components
        parts = filename.replace('.json', '').split('_')
        
        context = {
            'action': parts[0],  # What it does
            'domain': self.extract_domain(parts),
            'method': self.extract_method(parts), 
            'expertise_level': self.extract_expertise(parts),
            'performance_metric': self.extract_performance(parts),
            'resource_class': self.extract_resource_class(parts),
            'neuron_id': parts[-1]
        }
        
        # Generate natural language understanding
        context['natural_description'] = self.generate_description(context)
        context['use_cases'] = self.identify_use_cases(context)
        context['compatibility'] = self.assess_compatibility(context)
        
        return context
    
    def should_use_neuron(self, neuron_filename, current_task):
        """Determine if neuron is suitable for task based on filename context"""
        
        neuron_context = self.parse_neuron_context_from_filename(neuron_filename)
        task_requirements = self.analyze_task_requirements(current_task)
        
        # Match action type
        action_match = self.calculate_action_compatibility(
            neuron_context['action'], task_requirements['required_action']
        )
        
        # Match domain expertise
        domain_match = self.calculate_domain_compatibility(
            neuron_context['domain'], task_requirements['domain']
        )
        
        # Check performance requirements
        performance_match = self.check_performance_requirements(
            neuron_context['performance_metric'], task_requirements['min_performance']
        )
        
        # Overall suitability score
        suitability_score = (
            action_match * 0.4 + 
            domain_match * 0.3 + 
            performance_match * 0.3
        )
        
        return suitability_score > 0.7
```

### Cross-Neuron Communication with Context
```python
def send_contextual_message(sender_filename, receiver_filename, message):
    """Send message between neurons using filename context"""
    
    # Parse contexts from filenames
    sender_context = parse_neuron_context_from_filename(sender_filename)
    receiver_context = parse_neuron_context_from_filename(receiver_filename)
    
    # Create context-aware message
    contextual_message = {
        'original_message': message,
        'sender_context': {
            'action': sender_context['action'],
            'domain': sender_context['domain'],
            'expertise': sender_context['expertise_level'],
            'performance': sender_context['performance_metric']
        },
        'receiver_context': {
            'action': receiver_context['action'],
            'domain': receiver_context['domain'], 
            'expertise': receiver_context['expertise_level'],
            'performance': receiver_context['performance_metric']
        },
        'context_bridge': find_context_bridge(sender_context, receiver_context),
        'translation_needed': requires_context_translation(sender_context, receiver_context)
    }
    
    # Determine message filename based on contexts
    message_filename = generate_contextual_message_filename(
        sender_context, receiver_context, message
    )
    
    # Save message with contextual filename
    receiver_folder = os.path.dirname(receiver_filename)
    message_path = f"{receiver_folder}/{message_filename}"
    
    with open(message_path, 'w') as f:
        json.dump(contextual_message, f, indent=2)
    
    return message_path
```

---

## Dynamic Context Evolution

### Context Updates Based on Performance
```python
class ContextualNeuronEvolution:
    def update_neuron_context_filename(self, current_filename, performance_data):
        """Update filename to reflect evolved context"""
        
        current_context = parse_neuron_context_from_filename(current_filename)
        
        # Update performance metric
        new_performance = calculate_updated_performance(performance_data)
        
        # Check for expertise level promotion
        new_expertise = self.check_expertise_promotion(
            current_context['expertise_level'], 
            performance_data
        )
        
        # Check for specialization refinement
        new_specialization = self.refine_specialization(
            current_context, performance_data
        )
        
        # Generate updated filename
        updated_filename = self.generate_contextual_filename(
            action=current_context['action'],
            domain=current_context['domain'],
            method=new_specialization,
            expertise=new_expertise, 
            performance=new_performance,
            resource_class=current_context['resource_class'],
            neuron_id=current_context['neuron_id']
        )
        
        # Rename file if context changed significantly
        if self.context_change_significant(current_filename, updated_filename):
            self.rename_neuron_file(current_filename, updated_filename)
            self.update_references(current_filename, updated_filename)
        
        return updated_filename
    
    def check_expertise_promotion(self, current_expertise, performance_data):
        """Check if neuron deserves expertise level promotion"""
        
        promotion_thresholds = {
            'novice': {'success_rate': 0.75, 'tasks_completed': 50},
            'specialist': {'success_rate': 0.85, 'tasks_completed': 200},
            'expert': {'success_rate': 0.92, 'tasks_completed': 500},
            'master': {'success_rate': 0.96, 'tasks_completed': 1000}
        }
        
        current_performance = performance_data['success_rate']
        tasks_completed = performance_data['total_tasks']
        
        for level, requirements in promotion_thresholds.items():
            if (current_performance >= requirements['success_rate'] and 
                tasks_completed >= requirements['tasks_completed']):
                if self.expertise_levels[level] > self.expertise_levels[current_expertise]:
                    return level
        
        return current_expertise
```

---

## Context-Driven Recruitment

### Recruiting Based on Missing Context
```python
def recruit_neuron_for_missing_context(current_neurons, required_context):
    """Recruit specialist neuron for missing contextual capability"""
    
    # Analyze current neuron contexts
    existing_contexts = [
        parse_neuron_context_from_filename(filename) 
        for filename in current_neurons
    ]
    
    # Identify context gaps
    context_gaps = identify_missing_contexts(existing_contexts, required_context)
    
    # For each gap, design recruitment specification
    recruitment_specs = []
    
    for gap in context_gaps:
        # Generate contextual filename for needed neuron
        needed_filename = generate_contextual_filename(
            action=gap['missing_action'],
            domain=gap['missing_domain'],
            method=gap['suggested_method'],
            expertise='specialist',  # Start as specialist
            performance='75pct',     # Conservative initial estimate
            resource_class='medium',
            neuron_id=generate_new_neuron_id()
        )
        
        recruitment_specs.append({
            'needed_filename': needed_filename,
            'missing_context': gap,
            'recruitment_priority': gap['urgency_score'],
            'initial_training_data': gap['suggested_training']
        })
    
    # Sort by priority and recruit most needed
    recruitment_specs.sort(key=lambda x: x['recruitment_priority'], reverse=True)
    
    return recruitment_specs[0] if recruitment_specs else None
```

---

## Real-World Context Examples

### E-commerce Context Evolution
```
Initial:
basic_product_recommender_novice_45pct_n001.json

After learning:
recommend_products_using_collaborative_filtering_specialist_78pct_n001.json

After specialization:
recommend_products_considering_seasonal_trends_expert_89pct_n001.json

After mastery:
optimize_product_recommendations_with_profit_maximization_master_94pct_n001.json
```

### Scientific Research Context Evolution
```
Initial:
analyze_research_papers_novice_62pct_n002.json

Growth phases:
extract_insights_from_scientific_papers_specialist_81pct_n002.json
analyze_research_trends_across_multiple_papers_expert_88pct_n002.json
synthesize_research_findings_for_hypothesis_generation_master_93pct_n002.json
coordinate_multi_domain_research_analysis_validator_96pct_n002.json
```

### Creative Content Context Evolution
```
Initial:
generate_text_content_novice_55pct_n003.json

Evolution:
create_marketing_copy_with_persuasive_language_specialist_79pct_n003.json
generate_brand_narratives_maintaining_voice_consistency_expert_87pct_n003.json
orchestrate_multi_channel_content_campaigns_master_92pct_n003.json
validate_content_quality_across_creative_teams_coordinator_95pct_n003.json
```

---

## Context-Aware System Benefits

### 1. **Immediate Understanding**
- Any firefly bot instantly knows what each neuron does
- No time wasted reading documentation or guessing purpose
- Context inheritance through filename structure

### 2. **Intelligent Routing**
- Bots can match tasks to appropriate neurons by filename analysis
- Context compatibility calculated automatically
- Optimal neuron selection based on contextual fit

### 3. **Self-Documenting System**
- Filename evolution tracks neuron development history  
- Context changes reflect learning and specialization
- System architecture becomes self-explaining

### 4. **Efficient Communication**
- Messages include sender/receiver context automatically
- Context bridges identify translation needs
- Cross-domain communication enhanced by context awareness

### 5. **Organic Organization**
- Related contexts naturally cluster together
- Filesystem browsing reveals system capabilities
- Context gaps become immediately obvious for recruitment

This contextual key system transforms filenames from simple identifiers into rich semantic descriptors that provide complete operational context, enabling truly intelligent navigation and coordination within the firefly neural democracy.