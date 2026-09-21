#!/usr/bin/env python3
"""
Feedback Loop Optimizer - Learn from bot interactions to improve future assistance
Analyzes success/failure patterns and optimizes communication strategies
"""

import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path

class FeedbackLoopOptimizer:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.micro_updates_file = self.base_path / "micro_updates.log"
        self.learning_db_file = self.base_path / "communication_learning.json"
        
    def load_learning_database(self):
        """Load accumulated learning from past interactions"""
        try:
            with open(self.learning_db_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "success_patterns": {},
                "failure_patterns": {},
                "optimal_timing": {},
                "bot_preferences": {}
            }
    
    def save_learning_database(self, db):
        """Save updated learning database"""
        with open(self.learning_db_file, 'w') as f:
            json.dump(db, f, indent=2)
    
    def analyze_task_completion_patterns(self):
        """Analyze patterns in task completion success/failure"""
        try:
            with open(self.micro_updates_file, 'r') as f:
                updates = [line.strip() for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return {}
        
        patterns = {
            'successful_sequences': [],
            'blocked_sequences': [],
            'timing_patterns': defaultdict(list),
            'bot_efficiency': defaultdict(list)
        }
        
        # Analyze sequences of actions
        for i, update in enumerate(updates):
            if '|' not in update:
                continue
                
            parts = update.split('|')
            if len(parts) >= 4:
                time_str, bot, action, task = parts[:4]
                
                # Track timing between actions
                if i > 0:
                    prev_parts = updates[i-1].split('|')
                    if len(prev_parts) >= 4:
                        prev_time, prev_bot, prev_action, prev_task = prev_parts[:4]
                        patterns['timing_patterns'][f"{prev_action}->{action}"].append({
                            'bot_sequence': f"{prev_bot}->{bot}",
                            'time_gap': self.calculate_time_gap(prev_time, time_str)
                        })
                
                # Track successful completion patterns
                if action in ['COMPLETE', 'RESOLVED', 'SUCCESS']:
                    # Look for the start of this task
                    start_context = []
                    for j in range(max(0, i-5), i):
                        if task in updates[j]:
                            start_context.append(updates[j])
                    
                    patterns['successful_sequences'].append({
                        'task': task,
                        'bot': bot,
                        'context': start_context,
                        'completion_time': time_str
                    })
                
                # Track blocked patterns
                elif action in ['BLOCKED', 'FAILED', 'ERROR']:
                    # Analyze what led to this blockage
                    block_context = []
                    for j in range(max(0, i-3), i):
                        block_context.append(updates[j])
                    
                    patterns['blocked_sequences'].append({
                        'task': task,
                        'bot': bot,
                        'context': block_context,
                        'block_time': time_str
                    })
                
                # Track bot efficiency
                patterns['bot_efficiency'][bot].append({
                    'action': action,
                    'task': task,
                    'time': time_str
                })
        
        return patterns
    
    def calculate_time_gap(self, time1, time2):
        """Calculate time gap between two HH:MM time strings"""
        try:
            h1, m1 = map(int, time1.split(':'))
            h2, m2 = map(int, time2.split(':'))
            
            # Handle day rollover
            if h2 < h1 or (h2 == h1 and m2 < m1):
                h2 += 24
            
            return (h2 * 60 + m2) - (h1 * 60 + m1)
        except:
            return 0
    
    def identify_optimal_intervention_points(self, patterns):
        """Identify when foreman intervention is most effective"""
        intervention_analysis = {
            'successful_interventions': [],
            'failed_interventions': [],
            'optimal_timing': {}
        }
        
        # Analyze foreman interventions
        foreman_actions = [p for p in patterns['successful_sequences'] + patterns['blocked_sequences'] 
                          if p.get('bot') == 'foreman']
        
        for intervention in foreman_actions:
            context = intervention.get('context', [])
            
            # Determine if intervention was successful by looking ahead
            success_indicators = ['COMPLETE', 'RESOLVED', 'START', 'PROGRESS']
            
            # This is simplified - in practice would analyze subsequent updates
            if any(indicator in str(context) for indicator in success_indicators):
                intervention_analysis['successful_interventions'].append(intervention)
            else:
                intervention_analysis['failed_interventions'].append(intervention)
        
        return intervention_analysis
    
    def generate_optimization_recommendations(self, patterns, interventions):
        """Generate recommendations for improving communication"""
        recommendations = {
            'timing_optimizations': [],
            'knowledge_injection_improvements': [],
            'bot_coordination_enhancements': [],
            'proactive_assistance_opportunities': []
        }
        
        # Analyze timing patterns
        for sequence, timings in patterns['timing_patterns'].items():
            avg_time = sum(t['time_gap'] for t in timings) / len(timings) if timings else 0
            
            if avg_time > 15:  # More than 15 minutes between actions
                recommendations['timing_optimizations'].append({
                    'issue': f"Long delay in {sequence} sequence",
                    'average_delay': f"{avg_time:.1f} minutes",
                    'suggestion': "Consider proactive knowledge injection or alternative task assignment"
                })
        
        # Analyze blocked sequences
        blocked_tasks = Counter(p['task'] for p in patterns['blocked_sequences'])
        for task, count in blocked_tasks.most_common(3):
            if count > 1:
                recommendations['knowledge_injection_improvements'].append({
                    'issue': f"Task '{task}' blocked {count} times",
                    'suggestion': f"Create proactive guidance template for {task}",
                    'priority': "high" if count > 2 else "medium"
                })
        
        # Bot efficiency analysis
        for bot, actions in patterns['bot_efficiency'].items():
            success_rate = sum(1 for a in actions if a['action'] in ['COMPLETE', 'SUCCESS']) / len(actions) if actions else 0
            
            if success_rate < 0.7:
                recommendations['bot_coordination_enhancements'].append({
                    'bot': bot,
                    'success_rate': f"{success_rate:.1%}",
                    'suggestion': f"Increase assistance and resources for {bot}",
                    'focus_areas': self.identify_bot_struggle_areas(actions)
                })
        
        # Successful patterns to replicate
        successful_tasks = Counter(p['task'] for p in patterns['successful_sequences'])
        for task, count in successful_tasks.most_common(2):
            recommendations['proactive_assistance_opportunities'].append({
                'pattern': f"Task '{task}' completed successfully {count} times",
                'suggestion': f"Replicate success pattern from {task} for similar tasks",
                'replication_strategy': "Extract and template the successful approach"
            })
        
        return recommendations
    
    def identify_bot_struggle_areas(self, actions):
        """Identify specific areas where a bot struggles"""
        blocked_actions = [a for a in actions if a['action'] in ['BLOCKED', 'FAILED']]
        
        struggle_areas = []
        for action in blocked_actions:
            task = action['task']
            if 'k8s' in task or 'kubernetes' in task:
                struggle_areas.append("Kubernetes deployment")
            elif 'auth' in task or 'jwt' in task:
                struggle_areas.append("Authentication integration")
            elif 'database' in task or 'postgres' in task:
                struggle_areas.append("Database management")
            elif 'network' in task or 'api' in task:
                struggle_areas.append("Network connectivity")
        
        return list(set(struggle_areas))
    
    def update_learning_database(self, patterns, recommendations):
        """Update learning database with new insights"""
        db = self.load_learning_database()
        
        # Update success patterns
        for success in patterns['successful_sequences']:
            task = success['task']
            bot = success['bot']
            
            if task not in db['success_patterns']:
                db['success_patterns'][task] = []
            
            db['success_patterns'][task].append({
                'bot': bot,
                'timestamp': success['completion_time'],
                'context': success['context'][:2]  # Keep first 2 context items
            })
        
        # Update failure patterns
        for failure in patterns['blocked_sequences']:
            task = failure['task']
            
            if task not in db['failure_patterns']:
                db['failure_patterns'][task] = []
            
            db['failure_patterns'][task].append({
                'bot': failure['bot'],
                'timestamp': failure['block_time'],
                'context': failure['context'][:2]
            })
        
        # Update timing preferences
        for sequence, timings in patterns['timing_patterns'].items():
            avg_time = sum(t['time_gap'] for t in timings) / len(timings) if timings else 0
            db['optimal_timing'][sequence] = {
                'average_gap': avg_time,
                'sample_size': len(timings),
                'last_updated': datetime.now().isoformat()
            }
        
        self.save_learning_database(db)
        return db
    
    def generate_adaptive_templates(self, recommendations):
        """Generate adaptive communication templates based on learnings"""
        templates = []
        
        for rec in recommendations['knowledge_injection_improvements']:
            template = f"""# Adaptive Template: {rec['issue']}
            
## Proactive Guidance for {rec['suggestion']}
Priority: {rec.get('priority', 'medium')}

### When to use:
- Trigger: Bot shows signs of starting this task
- Timing: Before blockage occurs (predictive)
- Context: Based on {rec['issue']} pattern

### Guidance content:
- Step 1: [Specific instruction based on past successes]
- Step 2: [Common pitfall avoidance]
- Step 3: [Alternative approach if blocked]
- Resources: [Link to relevant files/documentation]
"""
            templates.append(template)
        
        return templates

def main():
    """Run feedback loop optimization analysis"""
    optimizer = FeedbackLoopOptimizer()
    
    print("=== Feedback Loop Optimizer ===")
    
    # Analyze patterns
    patterns = optimizer.analyze_task_completion_patterns()
    print(f"Analyzed {len(patterns.get('successful_sequences', []))} successful sequences")
    print(f"Analyzed {len(patterns.get('blocked_sequences', []))} blocked sequences")
    
    # Analyze interventions
    interventions = optimizer.identify_optimal_intervention_points(patterns)
    print(f"Identified {len(interventions.get('successful_interventions', []))} successful interventions")
    
    # Generate recommendations
    recommendations = optimizer.generate_optimization_recommendations(patterns, interventions)
    
    print("\n=== Optimization Recommendations ===")
    for category, recs in recommendations.items():
        if recs:
            print(f"\n{category.replace('_', ' ').title()}:")
            for i, rec in enumerate(recs[:2], 1):  # Show top 2 per category
                print(f"  {i}. {rec.get('issue') or rec.get('pattern', 'Optimization opportunity')}")
                print(f"     → {rec.get('suggestion', 'No specific suggestion')}")
    
    # Update learning database
    db = optimizer.update_learning_database(patterns, recommendations)
    print(f"\n✅ Learning database updated with {len(db['success_patterns'])} success patterns")
    
    return recommendations

if __name__ == "__main__":
    main()