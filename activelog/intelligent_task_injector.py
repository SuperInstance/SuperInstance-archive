#!/usr/bin/env python3
"""
Intelligent Task Injector - Proactive knowledge insertion system
Monitors bot progress and injects relevant knowledge/tasks before puzzles occur
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path

class IntelligentTaskInjector:
    def __init__(self):
        self.base_path = Path("/home/activeloguser/activelog")
        self.micro_updates_file = self.base_path / "micro_updates.log"
        self.knowledge_base = self.load_knowledge_base()
        self.injection_log = self.base_path / "knowledge_injections.log"
        
    def load_knowledge_base(self):
        """Load predictive assistance patterns"""
        try:
            with open(self.base_path / "predictive_assistance_system.py", 'r') as f:
                content = f.read()
                # Extract JSON from Python file (simplified parsing)
                start = content.find('{')
                end = content.rfind('}') + 1
                return json.loads(content[start:end])
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return {}
    
    def analyze_recent_updates(self, limit=10):
        """Analyze recent bot updates for trigger patterns"""
        try:
            with open(self.micro_updates_file, 'r') as f:
                lines = f.readlines()
                recent = [line.strip() for line in lines[-limit:] if line.strip()]
                return recent
        except FileNotFoundError:
            return []
    
    def detect_trigger_patterns(self, updates):
        """Detect patterns that should trigger knowledge injection"""
        triggers = []
        patterns = self.knowledge_base.get('trigger_patterns', {})
        
        for pattern_name, pattern_config in patterns.items():
            trigger_regex = pattern_config.get('trigger', '')
            
            for update in updates:
                if re.search(trigger_regex, update, re.IGNORECASE):
                    triggers.append({
                        'pattern': pattern_name,
                        'config': pattern_config,
                        'matching_update': update,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return triggers
    
    def check_phase_transitions(self):
        """Check for phase transitions that should trigger proactive knowledge"""
        transitions = []
        schedule = self.knowledge_base.get('proactive_knowledge_schedule', {}).get('phase_transitions', {})
        
        # Check file-based conditions
        for phase_name, phase_config in schedule.items():
            condition = phase_config.get('condition', '')
            
            if 'k8s-ready.flag exists' in condition:
                if os.path.exists('/tmp/k8s-ready.flag'):
                    transitions.append({
                        'phase': phase_name,
                        'config': phase_config,
                        'trigger': 'k8s-ready.flag detected'
                    })
            
            if 'auth-service-ready.flag exists' in condition:
                if os.path.exists('/tmp/auth-service-ready.flag'):
                    transitions.append({
                        'phase': phase_name, 
                        'config': phase_config,
                        'trigger': 'auth-service-ready.flag detected'
                    })
            
            # Check micro-updates for activity patterns
            if 'activelog.*START' in condition or 'fitness.*schema' in condition:
                recent_updates = self.analyze_recent_updates(5)
                for update in recent_updates:
                    if re.search(r'activelog.*START|fitness.*schema', update, re.IGNORECASE):
                        transitions.append({
                            'phase': phase_name,
                            'config': phase_config,
                            'trigger': f'Activity pattern: {update}'
                        })
        
        return transitions
    
    def inject_knowledge_to_bot(self, bot_name, knowledge_type, content):
        """Inject knowledge into specific bot log"""
        bot_log_file = self.base_path / f"bot_{bot_name}_log.txt"
        
        if not bot_log_file.exists():
            return False
        
        injection_content = f"""
## 💡 PREDICTIVE ASSISTANCE INJECTED - {datetime.now().strftime('%H:%M')}

### {knowledge_type.upper().replace('_', ' ')}:
{content}

### TIMING: Injected proactively to prevent common issues
### SOURCE: Intelligent Task Injector based on pattern analysis
"""
        
        # Insert after "NEXT TASKS FROM FOREMAN" section
        try:
            with open(bot_log_file, 'r') as f:
                content_lines = f.readlines()
            
            # Find insertion point
            insert_index = -1
            for i, line in enumerate(content_lines):
                if "## NEXT TASKS FROM FOREMAN:" in line:
                    insert_index = i + 1
                    break
            
            if insert_index > 0:
                content_lines.insert(insert_index, injection_content + "\n")
                
                with open(bot_log_file, 'w') as f:
                    f.writelines(content_lines)
                
                # Log the injection
                with open(self.injection_log, 'a') as f:
                    f.write(f"{datetime.now().isoformat()}|{bot_name}|{knowledge_type}|SUCCESS\n")
                
                return True
                
        except Exception as e:
            print(f"Error injecting knowledge to {bot_name}: {e}")
            
        return False
    
    def create_quality_templates(self, template_type):
        """Create quality assurance templates based on detected patterns"""
        templates = {
            'testing_checklist': """# Testing Checklist - Right First Time
- [ ] Health endpoint responds (curl http://service:port/health)
- [ ] Authentication works (test JWT token validation)
- [ ] Database connection established (check logs for connection errors)
- [ ] Required environment variables set
- [ ] Service discovery functional (can reach other services)
- [ ] Resource limits configured (CPU/memory constraints)
""",
            'troubleshooting_guide': """# Common Issues Troubleshooting Guide
1. **Service Won't Start**: Check port conflicts, environment variables, dependencies
2. **Database Connection**: Verify connection string, network access, credentials
3. **Authentication Fails**: Check JWT secret consistency, token expiry, CORS settings
4. **K8s Deployment Issues**: Verify manifests, check pod logs, network policies
5. **Docker Fallback**: Use docker-compose when K8s unstable
"""
        }
        
        template_content = templates.get(template_type, "# Template not found")
        template_file = self.base_path / f"{template_type}_generated.md"
        
        with open(template_file, 'w') as f:
            f.write(template_content)
        
        return template_file
    
    def analyze_and_inject(self):
        """Main analysis and injection cycle"""
        results = {
            'triggers_detected': 0,
            'phase_transitions': 0,
            'injections_made': 0,
            'templates_created': 0
        }
        
        # Analyze recent updates for trigger patterns
        recent_updates = self.analyze_recent_updates()
        triggers = self.detect_trigger_patterns(recent_updates)
        results['triggers_detected'] = len(triggers)
        
        # Process triggers
        for trigger in triggers:
            knowledge = trigger['config'].get('knowledge', {})
            inject_to = trigger['config'].get('inject_to', '')
            
            if isinstance(inject_to, list):
                target_bots = inject_to
            else:
                target_bots = [inject_to]
            
            for bot in target_bots:
                if self.inject_knowledge_to_bot(
                    bot, 
                    knowledge.get('title', 'Predictive Assistance'),
                    knowledge.get('content', 'No content available')
                ):
                    results['injections_made'] += 1
        
        # Check phase transitions
        transitions = self.check_phase_transitions()
        results['phase_transitions'] = len(transitions)
        
        # Process phase transitions
        for transition in transitions:
            injections = transition['config'].get('inject', [])
            for injection in injections:
                bot = injection.get('bot', '')
                knowledge_type = injection.get('knowledge_type', '')
                files = injection.get('files', [])
                content = injection.get('content', '')
                
                if files:
                    file_content = f"Ready files: {', '.join(files)}"
                    if content:
                        file_content += f"\n\nAdditional context: {content}"
                else:
                    file_content = content
                
                if self.inject_knowledge_to_bot(bot, knowledge_type, file_content):
                    results['injections_made'] += 1
        
        return results

def main():
    """Run intelligent task injection analysis"""
    injector = IntelligentTaskInjector()
    results = injector.analyze_and_inject()
    
    print(f"=== Intelligent Task Injector Results ===")
    print(f"Triggers detected: {results['triggers_detected']}")
    print(f"Phase transitions: {results['phase_transitions']}")
    print(f"Knowledge injections made: {results['injections_made']}")
    print(f"Templates created: {results['templates_created']}")
    
    if results['injections_made'] > 0:
        print(f"✅ {results['injections_made']} proactive knowledge injections delivered")
    else:
        print("ℹ️  No knowledge injections needed at this time")

if __name__ == "__main__":
    main()