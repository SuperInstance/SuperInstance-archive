#!/usr/bin/env python3
"""
Dynamic Role Adaptation System
Allows bots to fluidly change roles and responsibilities based on swarm needs
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

class DynamicRoleManager:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.role_definitions = self.create_flexible_role_definitions()
        self.skill_matrix = self.create_skill_matrix()
        self.adaptation_history = []
        
    def create_flexible_role_definitions(self):
        """Create fluid role definitions that can be mixed and matched"""
        return {
            'infrastructure_specialist': {
                'core_skills': ['kubernetes', 'docker', 'networking', 'security'],
                'secondary_skills': ['monitoring', 'deployment', 'troubleshooting'],
                'can_assist_with': ['service_deployment', 'database_setup'],
                'teaching_capability': ['container_orchestration', 'network_config']
            },
            'service_architect': {
                'core_skills': ['api_design', 'database', 'authentication', 'integration'],
                'secondary_skills': ['testing', 'documentation', 'performance'],
                'can_assist_with': ['domain_logic', 'infrastructure_setup'],
                'teaching_capability': ['rest_apis', 'database_design', 'auth_patterns']
            },
            'domain_expert': {
                'core_skills': ['business_logic', 'user_experience', 'data_modeling'],
                'secondary_skills': ['testing', 'integration', 'validation'],
                'can_assist_with': ['service_requirements', 'api_specifications'],
                'teaching_capability': ['domain_modeling', 'user_requirements']
            },
            'full_stack_generalist': {
                'core_skills': ['adaptability', 'problem_solving', 'communication'],
                'secondary_skills': ['all_technical_areas'],
                'can_assist_with': ['any_task'],
                'teaching_capability': ['cross_functional_collaboration']
            },
            'quality_assurance_specialist': {
                'core_skills': ['testing', 'validation', 'documentation', 'standards'],
                'secondary_skills': ['automation', 'monitoring', 'compliance'],
                'can_assist_with': ['any_task_quality_review'],
                'teaching_capability': ['testing_strategies', 'quality_processes']
            },
            'integration_coordinator': {
                'core_skills': ['system_integration', 'communication', 'coordination'],
                'secondary_skills': ['troubleshooting', 'planning', 'optimization'],
                'can_assist_with': ['cross_team_collaboration', 'dependency_management'],
                'teaching_capability': ['integration_patterns', 'coordination_strategies']
            }
        }
    
    def create_skill_matrix(self):
        """Create dynamic skill assessment matrix for all bots"""
        return {
            'infrastructure': {
                'kubernetes': {'level': 9, 'confidence': 95, 'recent_success': True},
                'docker': {'level': 9, 'confidence': 98, 'recent_success': True},
                'networking': {'level': 8, 'confidence': 85, 'recent_success': True},
                'monitoring': {'level': 8, 'confidence': 90, 'recent_success': True},
                'database': {'level': 6, 'confidence': 70, 'recent_success': False},
                'api_design': {'level': 5, 'confidence': 60, 'recent_success': False}
            },
            'services': {
                'api_design': {'level': 9, 'confidence': 95, 'recent_success': True},
                'database': {'level': 9, 'confidence': 98, 'recent_success': True},
                'authentication': {'level': 9, 'confidence': 95, 'recent_success': True},
                'testing': {'level': 7, 'confidence': 80, 'recent_success': True},
                'kubernetes': {'level': 6, 'confidence': 70, 'recent_success': False},
                'business_logic': {'level': 5, 'confidence': 65, 'recent_success': False}
            },
            'domains': {
                'business_logic': {'level': 9, 'confidence': 95, 'recent_success': True},
                'data_modeling': {'level': 8, 'confidence': 90, 'recent_success': True},
                'user_experience': {'level': 7, 'confidence': 85, 'recent_success': True},
                'testing': {'level': 7, 'confidence': 80, 'recent_success': True},
                'authentication': {'level': 6, 'confidence': 75, 'recent_success': False},
                'deployment': {'level': 5, 'confidence': 60, 'recent_success': False}
            }
        }
    
    def assess_current_swarm_state(self):
        """Assess current state of the bot swarm"""
        try:
            with open(self.base_path / "micro_updates.log", 'r') as f:
                recent_updates = f.readlines()[-15:]
        except FileNotFoundError:
            recent_updates = []
        
        state_assessment = {
            'active_bots': set(),
            'current_tasks': defaultdict(list),
            'blocked_tasks': defaultdict(list),
            'completed_tasks': defaultdict(list),
            'skill_demands': defaultdict(int),
            'workload_distribution': defaultdict(int)
        }
        
        for update in recent_updates:
            if '|' in update:
                parts = update.split('|')
                if len(parts) >= 4:
                    time_str, bot, action, task = parts[:4]
                    
                    state_assessment['active_bots'].add(bot)
                    state_assessment['workload_distribution'][bot] += 1
                    
                    if action == 'BLOCKED' or action == 'CRITICAL':
                        state_assessment['blocked_tasks'][bot].append(task)
                        # Infer skill demand from blocked task
                        self.infer_skill_demand(task, state_assessment['skill_demands'])
                    elif action == 'COMPLETE':
                        state_assessment['completed_tasks'][bot].append(task)
                    else:
                        state_assessment['current_tasks'][bot].append(task)
        
        return state_assessment
    
    def infer_skill_demand(self, task, skill_demands):
        """Infer what skills are needed from blocked tasks"""
        task_lower = task.lower()
        
        skill_keywords = {
            'kubernetes': ['k8s', 'kubectl', 'pod', 'deployment', 'cluster'],
            'docker': ['docker', 'container', 'image'],
            'networking': ['network', 'dns', 'api', 'connectivity'],
            'database': ['db', 'postgres', 'sql', 'schema', 'migration'],
            'authentication': ['auth', 'jwt', 'token', 'login'],
            'monitoring': ['monitor', 'health', 'metrics', 'logs'],
            'business_logic': ['domain', 'business', 'logic', 'workflow'],
            'integration': ['integration', 'api', 'service', 'communication']
        }
        
        for skill, keywords in skill_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                skill_demands[skill] += 1
    
    def suggest_role_adaptations(self, swarm_state):
        """Suggest role adaptations based on current swarm needs"""
        adaptations = []
        
        # Identify skill gaps
        for skill, demand in swarm_state['skill_demands'].items():
            if demand > 0:
                # Find bot with this skill who isn't overloaded
                available_helpers = []
                
                for bot, skills in self.skill_matrix.items():
                    if skill in skills and skills[skill]['level'] >= 7:
                        current_workload = swarm_state['workload_distribution'].get(bot, 0)
                        if current_workload < 5:  # Not overloaded
                            available_helpers.append({
                                'bot': bot,
                                'skill_level': skills[skill]['level'],
                                'confidence': skills[skill]['confidence'],
                                'workload': current_workload
                            })
                
                if available_helpers:
                    # Sort by skill level and availability
                    best_helper = sorted(
                        available_helpers, 
                        key=lambda x: (x['skill_level'], -x['workload'])
                    )[-1]
                    
                    adaptations.append({
                        'type': 'skill_assistance',
                        'helper_bot': best_helper['bot'],
                        'skill': skill,
                        'skill_level': best_helper['skill_level'],
                        'urgency': min(demand * 20, 100),
                        'adaptation_type': 'temporary_cross_training'
                    })
        
        # Identify workload imbalances
        if swarm_state['workload_distribution']:
            max_workload = max(swarm_state['workload_distribution'].values())
            min_workload = min(swarm_state['workload_distribution'].values())
            
            if max_workload - min_workload > 3:  # Significant imbalance
                overloaded_bot = max(
                    swarm_state['workload_distribution'].items(), 
                    key=lambda x: x[1]
                )[0]
                underutilized_bot = min(
                    swarm_state['workload_distribution'].items(),
                    key=lambda x: x[1]
                )[0]
                
                adaptations.append({
                    'type': 'workload_rebalancing',
                    'overloaded_bot': overloaded_bot,
                    'helper_bot': underutilized_bot,
                    'urgency': (max_workload - min_workload) * 10,
                    'adaptation_type': 'task_redistribution'
                })
        
        return adaptations
    
    def create_cross_training_program(self, adaptations):
        """Create cross-training programs for skill sharing"""
        programs = []
        
        for adaptation in adaptations:
            if adaptation['type'] == 'skill_assistance':
                program = {
                    'program_id': f"cross_train_{adaptation['skill']}_{int(datetime.now().timestamp())}",
                    'teacher_bot': adaptation['helper_bot'],
                    'skill': adaptation['skill'],
                    'learning_resources': self.get_learning_resources(adaptation['skill']),
                    'practical_exercises': self.get_practical_exercises(adaptation['skill']),
                    'success_criteria': self.get_success_criteria(adaptation['skill']),
                    'duration_estimate': '30-60 minutes',
                    'urgency': adaptation['urgency']
                }
                programs.append(program)
        
        return programs
    
    def get_learning_resources(self, skill):
        """Get learning resources for specific skills"""
        resources = {
            'kubernetes': [
                'k8s_deployment_template.yaml',
                'kubectl_cheat_sheet.md',
                'kubernetes troubleshooting guide'
            ],
            'authentication': [
                'jwt_middleware_template.py',
                'auth_integration_guide.md',
                'security_best_practices.md'
            ],
            'database': [
                'activelog_fitness_schema.sql',
                'database_setup_template.sql',
                'postgres_optimization_guide.md'
            ],
            'docker': [
                'docker_compose_services.yml',
                'dockerfile_best_practices.md',
                'container_troubleshooting.md'
            ]
        }
        
        return resources.get(skill, ['General documentation', 'Online tutorials'])
    
    def get_practical_exercises(self, skill):
        """Get practical exercises for skill development"""
        exercises = {
            'kubernetes': [
                'Deploy a simple service to cluster',
                'Debug a failing pod',
                'Scale a deployment'
            ],
            'authentication': [
                'Implement JWT middleware',
                'Test token validation',
                'Configure CORS settings'
            ],
            'database': [
                'Create a table with proper indexes',
                'Write migration script',
                'Optimize slow query'
            ]
        }
        
        return exercises.get(skill, ['Hands-on practice', 'Code review'])
    
    def get_success_criteria(self, skill):
        """Define success criteria for skill acquisition"""
        criteria = {
            'kubernetes': 'Successfully deploy and troubleshoot a service',
            'authentication': 'Implement working JWT authentication',
            'database': 'Design and implement efficient database schema',
            'docker': 'Create and deploy optimized containers'
        }
        
        return criteria.get(skill, 'Demonstrate competency in practical application')
    
    def enable_role_switching(self, adaptations):
        """Enable temporary or permanent role switching"""
        role_switches = []
        
        for adaptation in adaptations:
            if adaptation.get('urgency', 0) > 70:  # High urgency
                switch = {
                    'type': 'emergency_role_switch',
                    'primary_bot': adaptation.get('overloaded_bot', ''),
                    'backup_bot': adaptation.get('helper_bot', ''),
                    'duration': 'until_crisis_resolved',
                    'authority_level': 'full_delegation',
                    'responsibilities': self.get_emergency_responsibilities(adaptation)
                }
                role_switches.append(switch)
            else:  # Normal assistance
                switch = {
                    'type': 'collaborative_assistance',
                    'lead_bot': adaptation.get('overloaded_bot', ''),
                    'assist_bot': adaptation.get('helper_bot', ''),
                    'duration': 'task_completion',
                    'authority_level': 'advisory',
                    'responsibilities': ['skill_sharing', 'task_support']
                }
                role_switches.append(switch)
        
        return role_switches
    
    def get_emergency_responsibilities(self, adaptation):
        """Define emergency responsibilities for role switches"""
        return [
            'Take over critical path tasks',
            'Coordinate with other bots',
            'Make tactical decisions',
            'Report status to foreman'
        ]

def main():
    """Demonstrate dynamic role adaptation system"""
    manager = DynamicRoleManager()
    
    print("=== Dynamic Role Adaptation System ===")
    
    # Assess current swarm state
    swarm_state = manager.assess_current_swarm_state()
    print(f"🔍 Active bots: {len(swarm_state['active_bots'])}")
    print(f"🚫 Blocked tasks: {sum(len(tasks) for tasks in swarm_state['blocked_tasks'].values())}")
    
    # Suggest adaptations
    adaptations = manager.suggest_role_adaptations(swarm_state)
    print(f"🔄 Suggested adaptations: {len(adaptations)}")
    
    # Create cross-training programs
    programs = manager.create_cross_training_program(adaptations)
    print(f"📚 Cross-training programs: {len(programs)}")
    
    # Enable role switching
    role_switches = manager.enable_role_switching(adaptations)
    print(f"🔀 Role switches enabled: {len(role_switches)}")
    
    # Save adaptation plan
    adaptation_plan = {
        'timestamp': datetime.now().isoformat(),
        'swarm_state': {k: dict(v) if hasattr(v, 'items') else list(v) for k, v in swarm_state.items()},
        'adaptations': adaptations,
        'programs': programs,
        'role_switches': role_switches
    }
    
    with open(manager.base_path / "dynamic_role_adaptation_plan.json", 'w') as f:
        json.dump(adaptation_plan, f, indent=2)
    
    print("✅ Dynamic role adaptation plan saved")
    
    return manager

if __name__ == "__main__":
    main()